import math
import threading
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot

from app.engines.base_speech_engine import SpeechEngine


class LiveStreamWorker(QObject):
    level_changed = Signal(int)
    elapsed_changed = Signal(int)
    state_changed = Signal(str)
    partial_text = Signal(str)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        engine: SpeechEngine,
        output_path: Path,
        device_index: int,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        agent_label: str,
        sample_rate: int = 16000,
        frame_ms: int = 100,
        silence_ms: int = 1100,
        pre_roll_ms: int = 500,
        minimum_phrase_ms: int = 350,
        maximum_phrase_seconds: float = 25.0,
        energy_threshold: float = 0.012,
    ) -> None:
        super().__init__()

        self._engine = engine
        self._output_path = output_path
        self._device_index = device_index
        self._language = language
        self._uppercase = uppercase
        self._show_timestamps = show_timestamps
        self._agent_label = agent_label
        self._sample_rate = sample_rate

        self._frame_samples = max(
            1,
            int(sample_rate * frame_ms / 1000),
        )
        self._silence_frames = max(
            1,
            int(silence_ms / frame_ms),
        )
        self._pre_roll_frames = max(
            1,
            int(pre_roll_ms / frame_ms),
        )
        self._minimum_phrase_seconds = minimum_phrase_ms / 1000.0
        self._maximum_phrase_samples = int(
            sample_rate * maximum_phrase_seconds
        )
        self._base_energy_threshold = energy_threshold

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._audio_lock = threading.Lock()

        self._callback_frames: deque[np.ndarray] = deque()
        self._all_frames: list[np.ndarray] = []

        self._phrase_frames: list[np.ndarray] = []
        self._pre_roll: deque[np.ndarray] = deque(
            maxlen=self._pre_roll_frames
        )

        self._speech_active = False
        self._silence_counter = 0
        self._processed_audio_seconds = 0.0
        self._noise_floor = 0.004

    def stop(self) -> None:
        self._stop_event.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._pause_event.set()
        else:
            self._pause_event.clear()

    @Slot()
    def run(self) -> None:
        started_at = time.monotonic()
        paused_total = 0.0
        pause_started: float | None = None

        try:
            self._output_path.parent.mkdir(parents=True, exist_ok=True)

            def callback(indata, frames, time_info, status) -> None:
                del frames, time_info, status

                if self._stop_event.is_set() or self._pause_event.is_set():
                    return

                chunk = np.asarray(
                    indata[:, 0],
                    dtype=np.float32,
                ).copy()

                with self._audio_lock:
                    self._callback_frames.append(chunk)
                    self._all_frames.append(chunk)

                peak = (
                    float(np.max(np.abs(chunk)))
                    if chunk.size
                    else 0.0
                )
                self.level_changed.emit(
                    min(100, int(peak * 180))
                )

            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                device=self._device_index,
                callback=callback,
                blocksize=self._frame_samples,
            ):
                self.state_changed.emit(
                    "ESCUCHANDO · VAD ACTIVO"
                )

                while not self._stop_event.is_set():
                    now = time.monotonic()

                    if self._pause_event.is_set():
                        if pause_started is None:
                            pause_started = now
                    elif pause_started is not None:
                        paused_total += now - pause_started
                        pause_started = None

                    active_pause = (
                        now - pause_started
                        if pause_started is not None
                        else 0.0
                    )

                    elapsed = max(
                        0,
                        int(
                            now
                            - started_at
                            - paused_total
                            - active_pause
                        ),
                    )
                    self.elapsed_changed.emit(elapsed)

                    if not self._pause_event.is_set():
                        self._process_available_frames()

                    time.sleep(0.05)

            self._process_available_frames()

            if self._phrase_frames:
                self._finalize_phrase(force=True)

            self._save_complete_audio()

            if not self._all_frames:
                raise RuntimeError(
                    "NO SE CAPTURÓ AUDIO. REVISA EL MICRÓFONO "
                    "Y SUS PERMISOS."
                )

            self.completed.emit(str(self._output_path))

        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def _process_available_frames(self) -> None:
        while True:
            with self._audio_lock:
                if not self._callback_frames:
                    break
                frame = self._callback_frames.popleft()

            self._process_frame(frame)

    def _process_frame(self, frame: np.ndarray) -> None:
        energy = self._rms(frame)
        threshold = max(
            self._base_energy_threshold,
            self._noise_floor * 2.4,
        )
        voiced = energy >= threshold

        if not self._speech_active and not voiced:
            self._noise_floor = (
                0.97 * self._noise_floor
                + 0.03 * energy
            )

        if voiced:
            if not self._speech_active:
                self._speech_active = True
                self._silence_counter = 0
                self._phrase_frames.extend(
                    list(self._pre_roll)
                )
                self._pre_roll.clear()
                self.state_changed.emit(
                    "VOZ DETECTADA · GRABANDO FRASE"
                )

            self._phrase_frames.append(frame)
            self._silence_counter = 0

        elif self._speech_active:
            self._phrase_frames.append(frame)
            self._silence_counter += 1

            if self._silence_counter >= self._silence_frames:
                self._finalize_phrase(force=False)

        else:
            self._pre_roll.append(frame)

        phrase_samples = sum(
            item.size for item in self._phrase_frames
        )

        if (
            self._speech_active
            and phrase_samples >= self._maximum_phrase_samples
        ):
            self._finalize_phrase(force=True)

    def _finalize_phrase(self, force: bool) -> None:
        if not self._phrase_frames:
            self._reset_phrase_state()
            return

        audio = np.concatenate(self._phrase_frames)
        duration = audio.size / float(self._sample_rate)

        trailing_silence_seconds = (
            self._silence_counter
            * self._frame_samples
            / float(self._sample_rate)
        )

        speech_duration = max(
            0.0,
            duration - trailing_silence_seconds,
        )

        if (
            not force
            and speech_duration < self._minimum_phrase_seconds
        ):
            self._processed_audio_seconds += duration
            self._reset_phrase_state()
            self.state_changed.emit(
                "ESCUCHANDO · VAD ACTIVO"
            )
            return

        self._transcribe_phrase(audio)
        self._reset_phrase_state()

        if not self._stop_event.is_set():
            self.state_changed.emit(
                "ESCUCHANDO · VAD ACTIVO"
            )

    def _reset_phrase_state(self) -> None:
        self._phrase_frames.clear()
        self._speech_active = False
        self._silence_counter = 0

    def _transcribe_phrase(self, audio: np.ndarray) -> None:
        duration = audio.size / float(self._sample_rate)

        chunk_path = self._output_path.parent / (
            f".{self._output_path.stem}_"
            f"{int(self._processed_audio_seconds * 1000):09d}.wav"
        )

        self._write_wav(chunk_path, audio)
        self.state_changed.emit(
            "TRANSCRIBIENDO FRASE DETECTADA"
        )

        try:
            result = self._engine.transcribe(
                audio_path=chunk_path,
                language=self._language,
                uppercase=self._uppercase,
                show_timestamps=False,
                progress_callback=None,
            )

            text = " ".join(
                segment.text.strip()
                for segment in result.segments
                if segment.text.strip()
            ).strip()

            if text:
                start = self._processed_audio_seconds
                end = (
                    self._processed_audio_seconds
                    + duration
                )

                if self._show_timestamps:
                    line = (
                        f"[{self._format_time(start)} - "
                        f"{self._format_time(end)}] "
                        f"{self._agent_label}: {text}"
                    )
                else:
                    line = (
                        f"{self._agent_label}: {text}"
                    )

                self.partial_text.emit(line)

        finally:
            self._processed_audio_seconds += duration
            chunk_path.unlink(missing_ok=True)

    def _save_complete_audio(self) -> None:
        with self._audio_lock:
            if not self._all_frames:
                return
            audio = np.concatenate(self._all_frames)

        self._write_wav(
            self._output_path,
            audio,
        )

    def _write_wav(
        self,
        path: Path,
        audio: np.ndarray,
    ) -> None:
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)

        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self._sample_rate)
            wav.writeframes(pcm.tobytes())

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

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return f"{minutes:02d}:{secs:02d}"
