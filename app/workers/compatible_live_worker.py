import math
import queue
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundcard as sc
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot

from app.engines.base_speech_engine import SpeechEngine


@dataclass
class PhraseJob:
    label: str
    audio: np.ndarray
    sample_rate: int
    started_at: float
    ended_at: float


class VadChannel:
    def __init__(
        self,
        label: str,
        sample_rate: int,
        output_callback,
        base_threshold: float,
        silence_ms: int = 700,
        frame_ms: int = 50,
        pre_roll_ms: int = 300,
        maximum_phrase_seconds: float = 8.0,
    ) -> None:
        self.label = label
        self.sample_rate = sample_rate
        self.output_callback = output_callback
        self.base_threshold = base_threshold

        self.frame_samples = max(
            1,
            int(sample_rate * frame_ms / 1000),
        )
        self.silence_frames = max(
            1,
            int(silence_ms / frame_ms),
        )
        self.pre_roll_limit = max(
            1,
            int(pre_roll_ms / frame_ms),
        )
        self.maximum_phrase_samples = int(
            sample_rate * maximum_phrase_seconds
        )

        self._pre_roll: list[np.ndarray] = []
        self._phrase: list[np.ndarray] = []
        self._active = False
        self._silence_count = 0
        self._noise_floor = 0.0004
        self._started_at = 0.0

    def process(
        self,
        frame: np.ndarray,
        session_time: float,
    ) -> None:
        rms = self._rms(frame)

        if not self._active:
            self._noise_floor = (
                self._noise_floor * 0.995
                + rms * 0.005
            )

        threshold = max(
            self.base_threshold,
            self._noise_floor * 3.0,
        )
        voiced = rms >= threshold

        if voiced:
            if not self._active:
                self._active = True
                pre_seconds = (
                    sum(
                        item.size
                        for item in self._pre_roll
                    )
                    / float(self.sample_rate)
                )
                self._started_at = max(
                    0.0,
                    session_time - pre_seconds,
                )
                self._phrase.extend(self._pre_roll)
                self._pre_roll.clear()

            self._phrase.append(frame)
            self._silence_count = 0

        elif self._active:
            self._phrase.append(frame)
            self._silence_count += 1

            if self._silence_count >= self.silence_frames:
                self.finalize(session_time)

        else:
            self._pre_roll.append(frame)

            if len(self._pre_roll) > self.pre_roll_limit:
                self._pre_roll.pop(0)

        total_samples = sum(
            item.size
            for item in self._phrase
        )

        if (
            self._active
            and total_samples
            >= self.maximum_phrase_samples
        ):
            self.finalize(session_time)

    def finalize(
        self,
        session_time: float,
    ) -> None:
        if not self._phrase:
            self._reset()
            return

        audio = np.concatenate(self._phrase)
        duration = audio.size / float(self.sample_rate)
        trailing = (
            self._silence_count
            * self.frame_samples
            / float(self.sample_rate)
        )
        voice_duration = max(0.0, duration - trailing)
        rms = self._rms(audio)

        if voice_duration >= 0.45 and rms >= self.base_threshold:
            self.output_callback(
                PhraseJob(
                    label=self.label,
                    audio=audio,
                    sample_rate=self.sample_rate,
                    started_at=self._started_at,
                    ended_at=max(
                        session_time,
                        self._started_at + duration,
                    ),
                )
            )

        self._reset()

    def _reset(self) -> None:
        self._pre_roll.clear()
        self._phrase.clear()
        self._active = False
        self._silence_count = 0

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        if frame.size == 0:
            return 0.0

        return float(
            math.sqrt(
                float(
                    np.mean(
                        np.square(
                            frame,
                            dtype=np.float32,
                        )
                    )
                )
                + 1e-12
            )
        )


class CompatibleLiveWorker(QObject):
    agent_level_changed = Signal(int)
    client_level_changed = Signal(int)
    elapsed_changed = Signal(int)
    state_changed = Signal(str)
    source_state_changed = Signal(str, str)
    phrase_ready = Signal(str, str, float, float)
    recording_paths_ready = Signal(str, str)
    completed = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        engine: SpeechEngine,
        output_base_path: Path,
        capture_agent: bool,
        capture_client: bool,
        agent_device_index: int | None,
        client_loopback_id: str | None,
        client_loopback_name: str | None,
        language: str,
        uppercase: bool,
        agent_label: str,
        client_label: str,
    ) -> None:
        super().__init__()

        self._engine = engine
        self._output_base_path = output_base_path
        self._capture_agent_enabled = capture_agent
        self._capture_client_enabled = capture_client
        self._agent_device_index = agent_device_index
        self._client_loopback_id = client_loopback_id
        self._client_loopback_name = client_loopback_name
        self._language = language
        self._uppercase = uppercase
        self._agent_label = agent_label
        self._client_label = client_label

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._jobs: queue.PriorityQueue = queue.PriorityQueue()
        self._sequence = 0
        self._sequence_lock = threading.Lock()
        self._errors: queue.Queue = queue.Queue()

        self._agent_ready = threading.Event()
        self._client_ready = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._pause_event.set()
        else:
            self._pause_event.clear()

    def _enqueue(self, job: PhraseJob) -> None:
        with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence

        self._jobs.put(
            (
                float(job.started_at),
                sequence,
                job,
            )
        )

    @Slot()
    def run(self) -> None:
        started = time.monotonic()

        agent_path = self._output_base_path.with_name(
            f"{self._output_base_path.stem}_AGENTE.wav"
        )
        client_path = self._output_base_path.with_name(
            f"{self._output_base_path.stem}_CLIENTE.wav"
        )

        try:
            self._output_base_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            agent_thread = None
            client_thread = None

            if self._capture_agent_enabled:
                agent_thread = threading.Thread(
                    target=self._capture_agent,
                    args=(started, agent_path),
                    daemon=True,
                )
                agent_thread.start()
            else:
                self._agent_ready.set()
                self.source_state_changed.emit(
                    self._agent_label,
                    "DESACTIVADO",
                )

            if self._capture_client_enabled:
                client_thread = threading.Thread(
                    target=self._capture_client,
                    args=(started, client_path),
                    daemon=True,
                )
                client_thread.start()
            else:
                self._client_ready.set()
                self.source_state_changed.emit(
                    self._client_label,
                    "DESACTIVADO",
                )

            self.recording_paths_ready.emit(
                str(agent_path),
                str(client_path),
            )

            deadline = time.monotonic() + 8.0

            while time.monotonic() < deadline:
                self._raise_pending_error()

                if (
                    self._agent_ready.is_set()
                    and self._client_ready.is_set()
                ):
                    break

                time.sleep(0.05)
            else:
                raise RuntimeError(
                    "NO SE PUDIERON INICIAR LAS FUENTES SELECCIONADAS."
                )

            self.state_changed.emit("ESCUCHANDO")

            while (
                not self._stop_event.is_set()
                or (
                    agent_thread is not None
                    and agent_thread.is_alive()
                )
                or (
                    client_thread is not None
                    and client_thread.is_alive()
                )
                or not self._jobs.empty()
            ):
                self.elapsed_changed.emit(
                    max(
                        0,
                        int(time.monotonic() - started),
                    )
                )
                self._raise_pending_error()

                try:
                    _, _, job = self._jobs.get(
                        timeout=0.08
                    )
                except queue.Empty:
                    continue

                self._transcribe(job)

            if agent_thread is not None:
                agent_thread.join(timeout=3)

            if client_thread is not None:
                client_thread.join(timeout=3)

            self.completed.emit(
                str(agent_path),
                str(client_path),
            )

        except Exception as exc:
            self._stop_event.set()
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def _raise_pending_error(self) -> None:
        if self._errors.empty():
            return

        source, message = self._errors.get_nowait()
        raise RuntimeError(
            f"{source}: {message}"
        )

    def _capture_agent(
        self,
        started: float,
        output_path: Path,
    ) -> None:
        """Captura estable con lectura bloqueante y frecuencia nativa."""

        try:
            if self._agent_device_index is None:
                raise RuntimeError(
                    "NO HAY MICRÓFONO SELECCIONADO."
                )

            info = sd.query_devices(
                self._agent_device_index,
                "input",
            )
            sample_rate = int(
                float(
                    info.get(
                        "default_samplerate",
                        44100,
                    )
                )
            )
            blocksize = max(
                1,
                int(sample_rate * 0.10),
            )

            vad = VadChannel(
                label=self._agent_label,
                sample_rate=sample_rate,
                output_callback=self._enqueue,
                base_threshold=0.00075,
                silence_ms=800,
                frame_ms=100,
                pre_roll_ms=400,
                maximum_phrase_seconds=10.0,
            )

            with wave.open(
                str(output_path),
                "wb",
            ) as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)

                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    device=self._agent_device_index,
                    blocksize=blocksize,
                    latency="high",
                ) as stream:
                    self._agent_ready.set()
                    self.source_state_changed.emit(
                        self._agent_label,
                        "ACTIVO",
                    )

                    consecutive_silent_blocks = 0

                    while not self._stop_event.is_set():
                        data, overflowed = stream.read(
                            blocksize
                        )

                        if overflowed:
                            self.state_changed.emit(
                                "MICRÓFONO: RECUPERANDO FLUJO"
                            )

                        if self._pause_event.is_set():
                            time.sleep(0.03)
                            continue

                        frame = np.asarray(
                            data[:, 0],
                            dtype=np.float32,
                        ).copy()

                        peak = (
                            float(np.max(np.abs(frame)))
                            if frame.size
                            else 0.0
                        )

                        if peak < 0.00005:
                            consecutive_silent_blocks += 1
                        else:
                            consecutive_silent_blocks = 0

                        # Reinicia el flujo si Windows entrega silencio continuo.
                        if consecutive_silent_blocks >= 30:
                            raise RuntimeError(
                                "WINDOWS DEJÓ DE ENTREGAR AUDIO DEL MICRÓFONO."
                            )

                        wav_file.writeframes(
                            self._to_pcm(frame)
                        )

                        self.agent_level_changed.emit(
                            min(
                                100,
                                int(peak * 2500),
                            )
                        )

                        vad.process(
                            frame,
                            max(
                                0.0,
                                time.monotonic() - started,
                            ),
                        )

                    vad.finalize(
                        max(
                            0.0,
                            time.monotonic() - started,
                        )
                    )

        except Exception as exc:
            self._errors.put(
                ("AGENTE", str(exc))
            )
            self._stop_event.set()


    def _capture_client(
        self,
        started: float,
        output_path: Path,
    ) -> None:
        sample_rate = 48000
        blocksize = 2400

        try:
            loopback = self._find_loopback()

            vad = VadChannel(
                label=self._client_label,
                sample_rate=sample_rate,
                output_callback=self._enqueue,
                base_threshold=0.0015,
                silence_ms=700,
                frame_ms=50,
            )

            with wave.open(
                str(output_path),
                "wb",
            ) as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)

                with loopback.recorder(
                    samplerate=sample_rate,
                    channels=1,
                    blocksize=blocksize,
                ) as recorder:
                    self._client_ready.set()
                    self.source_state_changed.emit(
                        self._client_label,
                        "ACTIVO",
                    )

                    while not self._stop_event.is_set():
                        data = recorder.record(
                            numframes=blocksize
                        )

                        if self._pause_event.is_set():
                            time.sleep(0.03)
                            continue

                        frame = np.asarray(
                            data,
                            dtype=np.float32,
                        ).reshape(-1)

                        wav_file.writeframes(
                            self._to_pcm(frame)
                        )

                        peak = (
                            float(np.max(np.abs(frame)))
                            if frame.size
                            else 0.0
                        )
                        self.client_level_changed.emit(
                            min(
                                100,
                                int(peak * 300),
                            )
                        )

                        vad.process(
                            frame,
                            max(
                                0.0,
                                time.monotonic() - started,
                            ),
                        )

                    vad.finalize(
                        max(
                            0.0,
                            time.monotonic() - started,
                        )
                    )

        except Exception as exc:
            self._errors.put(
                ("CLIENTE", str(exc))
            )
            self._stop_event.set()

    def _find_loopback(self):
        loopbacks = [
            item
            for item in sc.all_microphones(
                include_loopback=True
            )
            if bool(
                getattr(
                    item,
                    "isloopback",
                    False,
                )
            )
        ]

        for device in loopbacks:
            if str(device.id) == str(
                self._client_loopback_id
            ):
                return device

        target = " ".join(
            str(
                self._client_loopback_name
                or ""
            )
            .lower()
            .split()
        )

        for device in loopbacks:
            current = " ".join(
                device.name.lower().split()
            )
            if (
                current == target
                or current in target
                or target in current
            ):
                return device

        raise RuntimeError(
            "NO SE ENCONTRÓ LA SALIDA DEL PC SELECCIONADA."
        )

    def _transcribe(self, job: PhraseJob) -> None:
        rms = VadChannel._rms(job.audio)
        minimum_rms = (
            0.00070
            if job.label == self._agent_label
            else 0.0015
        )

        if rms < minimum_rms:
            return

        audio_16k = self._resample(
            job.audio,
            job.sample_rate,
            16000,
        )

        temporary_path = (
            self._output_base_path.parent
            / (
                f".{self._output_base_path.stem}_"
                f"{job.label}_"
                f"{int(job.started_at * 1000):09d}.wav"
            )
        )

        self._write_wav(
            temporary_path,
            audio_16k,
            16000,
        )
        self.state_changed.emit(
            f"TRANSCRIBIENDO {job.label}"
        )

        try:
            result = self._engine.transcribe_live(
                audio_path=temporary_path,
                language=self._language,
                uppercase=self._uppercase,
            )

            text = " ".join(
                segment.text.strip()
                for segment in result.segments
                if segment.text.strip()
            ).strip()

            if text:
                self.phrase_ready.emit(
                    job.label,
                    text,
                    job.started_at,
                    job.ended_at,
                )

        finally:
            temporary_path.unlink(
                missing_ok=True
            )

            if not self._stop_event.is_set():
                self.state_changed.emit(
                    "ESCUCHANDO"
                )

    @staticmethod
    def _resample(
        audio: np.ndarray,
        source_rate: int,
        target_rate: int,
    ) -> np.ndarray:
        if source_rate == target_rate or audio.size == 0:
            return audio.astype(
                np.float32,
                copy=False,
            )

        duration = audio.size / float(source_rate)
        target_size = max(
            1,
            int(duration * target_rate),
        )

        old_positions = np.linspace(
            0.0,
            1.0,
            audio.size,
            endpoint=False,
        )
        new_positions = np.linspace(
            0.0,
            1.0,
            target_size,
            endpoint=False,
        )

        return np.interp(
            new_positions,
            old_positions,
            audio,
        ).astype(np.float32)

    @staticmethod
    def _write_wav(
        path: Path,
        audio: np.ndarray,
        sample_rate: int,
    ) -> None:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(
                CompatibleLiveWorker._to_pcm(audio)
            )

    @staticmethod
    def _to_pcm(audio: np.ndarray) -> bytes:
        clipped = np.clip(
            audio,
            -1.0,
            1.0,
        )
        pcm = (
            clipped * 32767.0
        ).astype(np.int16)

        return pcm.tobytes()
