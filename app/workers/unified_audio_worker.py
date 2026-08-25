from __future__ import annotations

import math
import queue
import re
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
from app.services.audio_device_service import AudioDeviceService


@dataclass
class PhraseJob:
    label: str
    audio: np.ndarray
    sample_rate: int
    started_at: float
    ended_at: float


class AdaptiveVad:
    def __init__(
        self,
        label: str,
        sample_rate: int,
        output_callback,
        base_rms: float,
        base_peak: float,
        frame_ms: int = 80,
        silence_ms: int = 920,
        maximum_seconds: float = 12.0,
    ) -> None:
        self.label = label
        self.sample_rate = sample_rate
        self.output_callback = output_callback
        self.base_rms = base_rms
        self.base_peak = base_peak
        self.silence_frames = max(1, int(silence_ms / frame_ms))
        self.maximum_samples = int(sample_rate * maximum_seconds)
        self.pre_roll_limit = max(1, int(480 / frame_ms))
        self.pre_roll: list[np.ndarray] = []
        self.parts: list[np.ndarray] = []
        self.active = False
        self.silent_frames = 0
        self.noise_rms = base_rms * 0.45
        self.noise_peak = base_peak * 0.45
        self.started_at = 0.0
        self.noise_filter = 35
        self._settings_lock = threading.Lock()

    def set_thresholds(
        self,
        base_rms: float,
        base_peak: float,
    ) -> None:
        with self._settings_lock:
            self.base_rms = max(1e-7, float(base_rms))
            self.base_peak = max(1e-7, float(base_peak))

    def set_noise_filter(self, value: int) -> None:
        with self._settings_lock:
            self.noise_filter = max(0, min(100, int(value)))

    def current_thresholds(self) -> tuple[float, float, float, float]:
        with self._settings_lock:
            base_rms = self.base_rms
            base_peak = self.base_peak
            noise_filter = self.noise_filter

        strength = noise_filter / 100.0
        rms_multiplier = 1.35 + (strength * 1.65)
        peak_multiplier = 1.25 + (strength * 1.45)

        return (
            base_rms,
            base_peak,
            rms_multiplier,
            peak_multiplier,
        )

    @staticmethod
    def rms(audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(math.sqrt(float(np.mean(np.square(audio, dtype=np.float32))) + 1e-12))

    def process(self, frame: np.ndarray, session_time: float) -> None:
        rms = self.rms(frame)
        peak = float(np.max(np.abs(frame))) if frame.size else 0.0
        if not self.active:
            self.noise_rms = self.noise_rms * 0.99 + rms * 0.01
            self.noise_peak = self.noise_peak * 0.99 + peak * 0.01

        (
            base_rms,
            base_peak,
            rms_multiplier,
            peak_multiplier,
        ) = self.current_thresholds()

        voiced = (
            rms >= max(base_rms, self.noise_rms * rms_multiplier)
            or peak >= max(base_peak, self.noise_peak * peak_multiplier)
        )

        if voiced:
            if not self.active:
                self.active = True
                pre_seconds = sum(item.size for item in self.pre_roll) / float(self.sample_rate)
                self.started_at = max(0.0, session_time - pre_seconds)
                self.parts.extend(self.pre_roll)
                self.pre_roll.clear()
            self.parts.append(frame)
            self.silent_frames = 0
        elif self.active:
            self.parts.append(frame)
            self.silent_frames += 1
            if self.silent_frames >= self.silence_frames:
                self.finalize(session_time)
        else:
            self.pre_roll.append(frame)
            if len(self.pre_roll) > self.pre_roll_limit:
                self.pre_roll.pop(0)

        if self.active and sum(item.size for item in self.parts) >= self.maximum_samples:
            self.finalize(session_time)

    def finalize(self, session_time: float) -> None:
        if not self.parts:
            self.reset()
            return
        audio = np.concatenate(self.parts)
        duration = audio.size / float(self.sample_rate)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        base_rms, base_peak, _, _ = self.current_thresholds()
        phrase_rms = self.rms(audio)

        if (
            duration >= 0.85
            and peak >= base_peak
            and phrase_rms >= base_rms
        ):
            self.output_callback(
                PhraseJob(
                    self.label,
                    audio,
                    self.sample_rate,
                    self.started_at,
                    max(session_time, self.started_at + duration),
                )
            )
        self.reset()

    def reset(self) -> None:
        self.pre_roll.clear()
        self.parts.clear()
        self.active = False
        self.silent_frames = 0


class UnifiedAudioWorker(QObject):
    agent_level = Signal(int)
    client_level = Signal(int)
    elapsed = Signal(int)
    state = Signal(str)
    sources = Signal(str)
    phrase = Signal(str, str, float, float)
    paths = Signal(str, str)
    completed = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        engine: SpeechEngine,
        base_path: Path,
        capture_agent: bool,
        capture_client: bool,
        input_index: int | None,
        input_rate: int,
        output_id: str,
        output_name: str,
        language: str,
        uppercase: bool,
        agent_label: str,
        client_label: str,
        agent_sensitivity: int = 75,
        client_sensitivity: int = 70,
        noise_filter: int = 35,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.base_path = base_path
        self.capture_agent_enabled = capture_agent
        self.capture_client_enabled = capture_client
        self.input_index = input_index
        self.input_rate = input_rate
        self.output_id = output_id
        self.output_name = output_name
        self.language = language
        self.uppercase = uppercase
        self.agent_label = agent_label
        self.client_label = client_label
        self.agent_sensitivity = max(0, min(100, int(agent_sensitivity)))
        self.client_sensitivity = max(0, min(100, int(client_sensitivity)))
        self.noise_filter = max(0, min(100, int(noise_filter)))
        self.agent_vad: AdaptiveVad | None = None
        self.client_vad: AdaptiveVad | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.errors: queue.Queue = queue.Queue()
        self.jobs: queue.PriorityQueue = queue.PriorityQueue()
        self.sequence = 0
        self.sequence_lock = threading.Lock()
        self.agent_ready = threading.Event()
        self.client_ready = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def set_paused(self, value: bool) -> None:
        self.pause_event.set() if value else self.pause_event.clear()

    def set_agent_sensitivity(self, value: int) -> None:
        self.agent_sensitivity = max(0, min(100, int(value)))
        vad = self.agent_vad

        if vad is not None:
            factor = self.sensitivity_factor(self.agent_sensitivity)
            vad.set_thresholds(
                0.00018 * factor,
                0.0015 * factor,
            )

    def set_client_sensitivity(self, value: int) -> None:
        self.client_sensitivity = max(0, min(100, int(value)))
        vad = self.client_vad

        if vad is not None:
            factor = self.sensitivity_factor(self.client_sensitivity)
            vad.set_thresholds(
                0.00040 * factor,
                0.0020 * factor,
            )

    def set_noise_filter(self, value: int) -> None:
        self.noise_filter = max(0, min(100, int(value)))

        if self.agent_vad is not None:
            self.agent_vad.set_noise_filter(self.noise_filter)

        if self.client_vad is not None:
            self.client_vad.set_noise_filter(self.noise_filter)

    @staticmethod
    def exception_text(source: str, exc: Exception) -> str:
        detail = str(exc).strip() or repr(exc).strip() or exc.__class__.__name__
        return f"No fue posible iniciar {source}. Detalle técnico: {detail}"

    def enqueue(self, job: PhraseJob) -> None:
        with self.sequence_lock:
            self.sequence += 1
            sequence = self.sequence
        self.jobs.put((job.started_at, sequence, job))

    @Slot()
    def run(self) -> None:
        started = time.monotonic()
        agent_path = self.base_path.with_name(self.base_path.stem + "_AGENTE.wav")
        client_path = self.base_path.with_name(self.base_path.stem + "_CLIENTE.wav")
        agent_thread = None
        client_thread = None

        try:
            self.base_path.parent.mkdir(parents=True, exist_ok=True)

            # Apertura secuencial: evita que entrada y loopback compitan al iniciar.
            if self.capture_agent_enabled:
                agent_thread = threading.Thread(
                    target=self.capture_agent,
                    args=(started, agent_path),
                    daemon=True,
                )
                agent_thread.start()
                self._wait_ready(self.agent_ready, "el micrófono")
            else:
                self.agent_ready.set()

            if self.capture_client_enabled:
                client_thread = threading.Thread(
                    target=self.capture_client,
                    args=(started, client_path),
                    daemon=True,
                )
                client_thread.start()
                self._wait_ready(self.client_ready, "el audio del cliente")
            else:
                self.client_ready.set()

            self.paths.emit(str(agent_path), str(client_path))
            active = []
            if self.capture_agent_enabled:
                active.append("AGENTE")
            if self.capture_client_enabled:
                active.append("CLIENTE")
            self.sources.emit(" · ".join(active) + " ACTIVOS")
            startup_deadline = time.monotonic() + 0.75

            while time.monotonic() < startup_deadline:
                self.raise_error()

                if self.stop_event.is_set():
                    raise RuntimeError(
                        "LA CAPTURA SE DETUVO DURANTE EL INICIO."
                    )

                time.sleep(0.05)

            self.state.emit("ESCUCHANDO")

            while True:
                self.raise_error()

                if self.stop_event.is_set():
                    break

                self.elapsed.emit(
                    int(time.monotonic() - started)
                )

                try:
                    _, _, job = self.jobs.get(
                        timeout=0.08
                    )
                except queue.Empty:
                    continue

                self.transcribe(job)

            self.raise_error()

            if agent_thread:
                agent_thread.join(timeout=3.0)
            if client_thread:
                client_thread.join(timeout=3.0)

            while not self.jobs.empty():
                _, _, job = self.jobs.get_nowait()
                self.transcribe(job)

            self.completed.emit(str(agent_path), str(client_path))
        except Exception as exc:
            self.stop_event.set()
            self.failed.emit(str(exc).strip() or repr(exc))
        finally:
            self.finished.emit()

    def _wait_ready(self, event: threading.Event, source: str) -> None:
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            self.raise_error()
            if event.is_set():
                return
            time.sleep(0.05)
        raise RuntimeError(f"No fue posible abrir {source} dentro del tiempo esperado.")

    def raise_error(self) -> None:
        if not self.errors.empty():
            raise RuntimeError(self.errors.get_nowait())

    @staticmethod
    def level(peak: float, full_scale: float) -> int:
        if peak <= 0:
            return 0
        return max(0, min(100, int(peak / full_scale * 100)))


    @staticmethod
    def sensitivity_factor(value: int) -> float:
        """
        Convierte 0-100 en un multiplicador del umbral:
        0 = menos sensible; 100 = más sensible.
        """
        normalized = max(0.0, min(1.0, value / 100.0))
        return 1.25 - (normalized * 0.95)

    def capture_agent(self, started: float, path: Path) -> None:
        try:
            if self.input_index is None:
                raise RuntimeError("No existe un micrófono seleccionado.")
            rate = int(self.input_rate or 48000)
            block = max(512, int(rate * 0.08))
            factor = self.sensitivity_factor(self.agent_sensitivity)
            vad = AdaptiveVad(
                self.agent_label,
                rate,
                self.enqueue,
                base_rms=0.00018 * factor,
                base_peak=0.0015 * factor,
                silence_ms=920,
                maximum_seconds=12.0,
            )
            vad.set_noise_filter(self.noise_filter)
            self.agent_vad = vad

            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(rate)
                with sd.InputStream(
                    samplerate=rate,
                    channels=1,
                    dtype="float32",
                    device=self.input_index,
                    blocksize=block,
                    latency="high",
                ) as stream:
                    self.agent_ready.set()
                    while not self.stop_event.is_set():
                        data, _ = stream.read(block)
                        if self.pause_event.is_set():
                            continue
                        audio = np.asarray(data[:, 0], dtype=np.float32).copy()
                        wav_file.writeframes(self.pcm(audio))
                        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                        self.agent_level.emit(self.level(peak, 0.035))
                        vad.process(audio, max(0.0, time.monotonic() - started))
                    vad.finalize(max(0.0, time.monotonic() - started))
        except Exception as exc:
            self.errors.put(self.exception_text("el micrófono del agente", exc))
            self.stop_event.set()

    def capture_client(self, started: float, path: Path) -> None:
        try:
            rate = 48000
            block = 3840
            loopback = AudioDeviceService.get_loopback(self.output_id, self.output_name)
            factor = self.sensitivity_factor(self.client_sensitivity)
            vad = AdaptiveVad(
                self.client_label,
                rate,
                self.enqueue,
                base_rms=0.00040 * factor,
                base_peak=0.0020 * factor,
                silence_ms=920,
                maximum_seconds=12.0,
            )
            vad.set_noise_filter(self.noise_filter)
            self.client_vad = vad

            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(rate)
                with loopback.recorder(
                    samplerate=rate,
                    channels=1,
                    blocksize=block,
                ) as recorder:
                    self.client_ready.set()
                    while not self.stop_event.is_set():
                        audio = np.asarray(
                            recorder.record(numframes=block),
                            dtype=np.float32,
                        ).reshape(-1)
                        if self.pause_event.is_set():
                            continue
                        wav_file.writeframes(self.pcm(audio))
                        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                        self.client_level.emit(self.level(peak, 0.20))
                        vad.process(audio, max(0.0, time.monotonic() - started))
                    vad.finalize(max(0.0, time.monotonic() - started))
        except Exception as exc:
            self.errors.put(self.exception_text("el audio del cliente", exc))
            self.stop_event.set()

    def transcribe(self, job: PhraseJob) -> None:
        audio = self.normalize(job.audio)
        if audio.size == 0:
            return
        temporary = self.base_path.parent / (
            f".{self.base_path.stem}_{job.label}_{int(job.started_at * 1000)}.wav"
        )
        self.write(temporary, self.resample(audio, job.sample_rate, 16000), 16000)
        self.state.emit(f"TRANSCRIBIENDO {job.label}")
        try:
            result = self.engine.transcribe_live(temporary, self.language, self.uppercase)
            text = " ".join(
                segment.text.strip()
                for segment in result.segments
                if segment.text.strip()
            ).strip()
            if text and not self.hallucination(text):
                self.phrase.emit(job.label, text, job.started_at, job.ended_at)
        finally:
            temporary.unlink(missing_ok=True)
            if not self.stop_event.is_set():
                self.state.emit("ESCUCHANDO")


    @staticmethod
    def normalize(audio: np.ndarray) -> np.ndarray:
        if not audio.size:
            return np.array([], dtype=np.float32)

        signal = np.asarray(audio, dtype=np.float32).reshape(-1)
        signal = signal - float(np.mean(signal))

        peak = float(np.max(np.abs(signal)))
        rms = float(
            np.sqrt(
                np.mean(
                    np.square(signal, dtype=np.float32)
                )
                + 1e-12
            )
        )

        if peak < 0.0012 or rms < 0.00016:
            return np.array([], dtype=np.float32)

        envelope_window = max(1, int(len(signal) / 250))

        if envelope_window > 1:
            kernel = (
                np.ones(envelope_window, dtype=np.float32)
                / envelope_window
            )
            envelope = np.convolve(
                np.abs(signal),
                kernel,
                mode="same",
            )
        else:
            envelope = np.abs(signal)

        threshold = max(
            0.00055,
            float(np.percentile(envelope, 30)) * 1.7,
        )
        active = np.flatnonzero(envelope >= threshold)

        if active.size:
            padding = max(1, int(len(signal) * 0.035))
            start = max(0, int(active[0]) - padding)
            end = min(len(signal), int(active[-1]) + padding)
            signal = signal[start:end]

        if signal.size < 8000:
            return np.array([], dtype=np.float32)

        rms = float(
            np.sqrt(
                np.mean(
                    np.square(signal, dtype=np.float32)
                )
                + 1e-12
            )
        )

        target_rms = 0.075
        gain = min(
            7.0,
            max(
                0.65,
                target_rms / max(rms, 1e-9),
            ),
        )

        signal = signal * gain
        signal = np.tanh(signal * 1.15) / np.tanh(1.15)

        return np.clip(
            signal,
            -0.98,
            0.98,
        ).astype(np.float32)

    @staticmethod
    def hallucination(text: str) -> bool:
        cleaned = " ".join(text.lower().split())
        words = re.findall(r"\w+", cleaned)

        if not words:
            return True

        if len(words) >= 5:
            repetition = max(
                words.count(word)
                for word in set(words)
            ) / len(words)

            if repetition >= 0.65:
                return True

        known_noise_phrases = {
            "conciencia en español",
            "subtítulos realizados por la comunidad",
            "gracias por ver",
            "hasta la próxima",
        }

        return cleaned in known_noise_phrases

    @staticmethod
    def resample(
        audio: np.ndarray,
        source_rate: int,
        target_rate: int,
    ) -> np.ndarray:
        if source_rate == target_rate or audio.size == 0:
            return audio.astype(np.float32, copy=False)

        size = max(
            1,
            int(audio.size * target_rate / float(source_rate)),
        )

        return np.interp(
            np.linspace(0.0, 1.0, size, endpoint=False),
            np.linspace(0.0, 1.0, audio.size, endpoint=False),
            audio,
        ).astype(np.float32)

    @staticmethod
    def pcm(audio: np.ndarray) -> bytes:
        return (
            np.clip(audio, -1.0, 1.0) * 32767.0
        ).astype(np.int16).tobytes()

    @classmethod
    def write(
        cls,
        path: Path,
        audio: np.ndarray,
        sample_rate: int,
    ) -> None:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(cls.pcm(audio))
