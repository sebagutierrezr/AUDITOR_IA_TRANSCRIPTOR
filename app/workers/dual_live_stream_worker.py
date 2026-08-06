import math
import queue
import threading
import time
import wave
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
    started_at: float
    ended_at: float


class VadChannel:
    def __init__(
        self,
        label: str,
        sample_rate: int,
        phrase_queue: queue.Queue,
        silence_ms: int = 1100,
        frame_ms: int = 100,
        pre_roll_ms: int = 500,
        minimum_phrase_ms: int = 300,
        maximum_phrase_seconds: float = 25.0,
        energy_threshold: float = 0.010,
    ) -> None:
        self.label = label
        self.sample_rate = sample_rate
        self.phrase_queue = phrase_queue

        self.frame_samples = int(
            sample_rate * frame_ms / 1000
        )
        self.silence_frames = max(
            1,
            int(silence_ms / frame_ms),
        )
        self.pre_roll_limit = max(
            1,
            int(pre_roll_ms / frame_ms),
        )
        self.minimum_phrase_seconds = minimum_phrase_ms / 1000.0
        self.maximum_phrase_samples = int(
            sample_rate * maximum_phrase_seconds
        )
        self.base_energy_threshold = energy_threshold

        self.pre_roll: list[np.ndarray] = []
        self.phrase_frames: list[np.ndarray] = []
        self.speech_active = False
        self.silence_counter = 0
        self.noise_floor = 0.003
        self.phrase_started_at = 0.0

    def process(
        self,
        frame: np.ndarray,
        session_time: float,
    ) -> None:
        energy = self._rms(frame)
        threshold = max(
            self.base_energy_threshold,
            self.noise_floor * 2.5,
        )
        voiced = energy >= threshold

        if not self.speech_active and not voiced:
            self.noise_floor = (
                self.noise_floor * 0.97
                + energy * 0.03
            )

        if voiced:
            if not self.speech_active:
                self.speech_active = True
                self.silence_counter = 0

                pre_seconds = (
                    sum(item.size for item in self.pre_roll)
                    / float(self.sample_rate)
                )
                self.phrase_started_at = max(
                    0.0,
                    session_time - pre_seconds,
                )

                self.phrase_frames.extend(
                    self.pre_roll
                )
                self.pre_roll.clear()

            self.phrase_frames.append(frame)
            self.silence_counter = 0

        elif self.speech_active:
            self.phrase_frames.append(frame)
            self.silence_counter += 1

            if self.silence_counter >= self.silence_frames:
                self.finalize(
                    session_time,
                    force=False,
                )

        else:
            self.pre_roll.append(frame)

            if len(self.pre_roll) > self.pre_roll_limit:
                self.pre_roll.pop(0)

        total_samples = sum(
            item.size for item in self.phrase_frames
        )

        if (
            self.speech_active
            and total_samples >= self.maximum_phrase_samples
        ):
            self.finalize(
                session_time,
                force=True,
            )

    def finalize(
        self,
        session_time: float,
        force: bool,
    ) -> None:
        if not self.phrase_frames:
            self._reset()
            return

        audio = np.concatenate(
            self.phrase_frames
        )
        duration = (
            audio.size
            / float(self.sample_rate)
        )
        trailing = (
            self.silence_counter
            * self.frame_samples
            / float(self.sample_rate)
        )
        speech_duration = max(
            0.0,
            duration - trailing,
        )

        if (
            force
            or speech_duration >= self.minimum_phrase_seconds
        ):
            self.phrase_queue.put(
                PhraseJob(
                    label=self.label,
                    audio=audio,
                    started_at=self.phrase_started_at,
                    ended_at=max(
                        self.phrase_started_at + duration,
                        session_time,
                    ),
                )
            )

        self._reset()

    def _reset(self) -> None:
        self.phrase_frames.clear()
        self.speech_active = False
        self.silence_counter = 0

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


class DualLiveStreamWorker(QObject):
    agent_level_changed = Signal(int)
    client_level_changed = Signal(int)
    elapsed_changed = Signal(int)
    state_changed = Signal(str)
    partial_text = Signal(str)
    source_ready = Signal(str)
    completed = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        engine: SpeechEngine,
        output_base_path: Path,
        agent_device_index: int,
        client_loopback_id: str,
        client_loopback_name: str,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        agent_label: str,
        client_label: str,
        sample_rate: int = 16000,
    ) -> None:
        super().__init__()

        self._engine = engine
        self._output_base_path = output_base_path
        self._agent_device_index = agent_device_index
        self._client_loopback_id = client_loopback_id
        self._client_loopback_name = client_loopback_name
        self._language = language
        self._uppercase = uppercase
        self._show_timestamps = show_timestamps
        self._agent_label = agent_label
        self._client_label = client_label
        self._sample_rate = sample_rate
        self._frame_samples = int(
            sample_rate * 0.10
        )

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._phrase_queue: queue.Queue[PhraseJob] = queue.Queue()
        self._capture_errors: queue.Queue[str] = queue.Queue()

        self._ready_events = {
            agent_label: threading.Event(),
            client_label: threading.Event(),
        }

        self._all_audio: dict[str, list[np.ndarray]] = {
            agent_label: [],
            client_label: [],
        }

        self._audio_locks = {
            agent_label: threading.Lock(),
            client_label: threading.Lock(),
        }

    def stop(self) -> None:
        self._stop_event.set()

    def set_paused(
        self,
        paused: bool,
    ) -> None:
        if paused:
            self._pause_event.set()
        else:
            self._pause_event.clear()

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

            client_loopback = self._resolve_loopback(
                self._client_loopback_id,
                self._client_loopback_name,
            )

            agent_channel = VadChannel(
                self._agent_label,
                self._sample_rate,
                self._phrase_queue,
                energy_threshold=0.010,
            )
            client_channel = VadChannel(
                self._client_label,
                self._sample_rate,
                self._phrase_queue,
                energy_threshold=0.006,
            )

            agent_thread = threading.Thread(
                target=self._capture_agent_with_sounddevice,
                args=(
                    agent_channel,
                    started,
                ),
                daemon=True,
            )

            client_thread = threading.Thread(
                target=self._capture_client_with_soundcard,
                args=(
                    client_loopback,
                    client_channel,
                    started,
                ),
                daemon=True,
            )

            agent_thread.start()
            client_thread.start()

            startup_deadline = time.monotonic() + 8.0

            while time.monotonic() < startup_deadline:
                if not self._capture_errors.empty():
                    raise RuntimeError(
                        self._capture_errors.get_nowait()
                    )

                if all(
                    event.is_set()
                    for event in self._ready_events.values()
                ):
                    break

                time.sleep(0.05)

            else:
                missing = [
                    label
                    for label, event
                    in self._ready_events.items()
                    if not event.is_set()
                ]

                self._stop_event.set()

                raise RuntimeError(
                    "NO SE PUDIERON INICIAR LAS FUENTES: "
                    + ", ".join(missing)
                )

            self.state_changed.emit(
                "ESCUCHANDO AGENTE Y CLIENTE"
            )

            while (
                not self._stop_event.is_set()
                or agent_thread.is_alive()
                or client_thread.is_alive()
                or not self._phrase_queue.empty()
            ):
                self.elapsed_changed.emit(
                    max(
                        0,
                        int(
                            time.monotonic()
                            - started
                        ),
                    )
                )

                if not self._capture_errors.empty():
                    raise RuntimeError(
                        self._capture_errors.get_nowait()
                    )

                try:
                    job = self._phrase_queue.get(
                        timeout=0.15
                    )
                except queue.Empty:
                    continue

                self._transcribe_job(job)

            agent_thread.join(timeout=3)
            client_thread.join(timeout=3)

            self._write_complete_audio(
                agent_path,
                self._agent_label,
            )
            self._write_complete_audio(
                client_path,
                self._client_label,
            )

            self.completed.emit(
                str(agent_path),
                str(client_path),
            )

        except Exception as exc:
            self._stop_event.set()
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def _capture_agent_with_sounddevice(
        self,
        channel: VadChannel,
        started: float,
    ) -> None:
        try:
            def callback(
                indata,
                frames,
                time_info,
                status,
            ) -> None:
                del frames, time_info, status

                if (
                    self._stop_event.is_set()
                    or self._pause_event.is_set()
                ):
                    return

                frame = np.asarray(
                    indata[:, 0],
                    dtype=np.float32,
                ).copy()

                with self._audio_locks[self._agent_label]:
                    self._all_audio[
                        self._agent_label
                    ].append(frame)

                peak = (
                    float(np.max(np.abs(frame)))
                    if frame.size
                    else 0.0
                )
                self.agent_level_changed.emit(
                    min(
                        100,
                        int(peak * 180),
                    )
                )

                channel.process(
                    frame,
                    max(
                        0.0,
                        time.monotonic() - started,
                    ),
                )

            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                device=self._agent_device_index,
                callback=callback,
                blocksize=self._frame_samples,
            ):
                self._ready_events[
                    self._agent_label
                ].set()
                self.source_ready.emit(
                    self._agent_label
                )

                while not self._stop_event.wait(0.10):
                    pass

            channel.finalize(
                max(
                    0.0,
                    time.monotonic() - started,
                ),
                force=True,
            )

        except Exception as exc:
            self._capture_errors.put(
                f"ERROR CAPTURANDO AGENTE: {exc}"
            )
            self._stop_event.set()

    def _capture_client_with_soundcard(
        self,
        loopback,
        channel: VadChannel,
        started: float,
    ) -> None:
        try:
            with loopback.recorder(
                samplerate=self._sample_rate,
                channels=1,
                blocksize=self._frame_samples,
            ) as recorder:
                self._ready_events[
                    self._client_label
                ].set()
                self.source_ready.emit(
                    self._client_label
                )

                while not self._stop_event.is_set():
                    frame = recorder.record(
                        numframes=self._frame_samples
                    )
                    frame = np.asarray(
                        frame,
                        dtype=np.float32,
                    ).reshape(-1)

                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        continue

                    with self._audio_locks[self._client_label]:
                        self._all_audio[
                            self._client_label
                        ].append(frame.copy())

                    peak = (
                        float(np.max(np.abs(frame)))
                        if frame.size
                        else 0.0
                    )
                    self.client_level_changed.emit(
                        min(
                            100,
                            int(peak * 180),
                        )
                    )

                    channel.process(
                        frame,
                        max(
                            0.0,
                            time.monotonic() - started,
                        ),
                    )

                channel.finalize(
                    max(
                        0.0,
                        time.monotonic() - started,
                    ),
                    force=True,
                )

        except Exception as exc:
            self._capture_errors.put(
                f"ERROR CAPTURANDO CLIENTE: {exc}"
            )
            self._stop_event.set()

    def _resolve_loopback(
        self,
        device_id: str,
        device_name: str,
    ):
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
            if str(device.id) == str(device_id):
                return device

        target = " ".join(
            device_name.lower().split()
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

        available = ", ".join(
            item.name for item in loopbacks
        ) or "NINGUNO"

        raise RuntimeError(
            "NO SE ENCONTRÓ LA SALIDA LOOPBACK "
            f"DEL CLIENTE. DISPONIBLES: {available}"
        )

    def _transcribe_job(
        self,
        job: PhraseJob,
    ) -> None:
        temp_path = self._output_base_path.with_name(
            f".{self._output_base_path.stem}_"
            f"{job.label}_"
            f"{int(job.started_at * 1000):09d}.wav"
        )

        self._write_wav(
            temp_path,
            job.audio,
        )
        self.state_changed.emit(
            f"TRANSCRIBIENDO {job.label}"
        )

        try:
            result = self._engine.transcribe(
                audio_path=temp_path,
                language=self._language,
                uppercase=self._uppercase,
                show_timestamps=False,
                progress_callback=None,
            )

            text = " ".join(
                item.text.strip()
                for item in result.segments
                if item.text.strip()
            ).strip()

            if not text:
                return

            if self._show_timestamps:
                line = (
                    f"[{self._format_time(job.started_at)} - "
                    f"{self._format_time(job.ended_at)}] "
                    f"{job.label}: {text}"
                )
            else:
                line = (
                    f"{job.label}: {text}"
                )

            self.partial_text.emit(line)

        finally:
            temp_path.unlink(
                missing_ok=True
            )

            if not self._stop_event.is_set():
                self.state_changed.emit(
                    "ESCUCHANDO AGENTE Y CLIENTE"
                )

    def _write_complete_audio(
        self,
        path: Path,
        label: str,
    ) -> None:
        with self._audio_locks[label]:
            frames = list(
                self._all_audio[label]
            )

        if not frames:
            return

        self._write_wav(
            path,
            np.concatenate(frames),
        )

    def _write_wav(
        self,
        path: Path,
        audio: np.ndarray,
    ) -> None:
        pcm = np.clip(
            audio,
            -1.0,
            1.0,
        )
        pcm = (
            pcm * 32767.0
        ).astype(np.int16)

        with wave.open(
            str(path),
            "wb",
        ) as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(
                self._sample_rate
            )
            wav.writeframes(
                pcm.tobytes()
            )

    @staticmethod
    def _format_time(
        seconds: float,
    ) -> str:
        total = max(
            0,
            int(seconds),
        )
        hours, remainder = divmod(
            total,
            3600,
        )
        minutes, secs = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )
