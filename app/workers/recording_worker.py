import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot


class RecordingWorker(QObject):
    level_changed = Signal(int)
    elapsed_changed = Signal(int)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        output_path: Path,
        device_index: int | None = None,
        sample_rate: int = 16000,
    ) -> None:
        super().__init__()
        self._output_path = output_path
        self._device_index = device_index
        self._sample_rate = sample_rate
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._frames: list[np.ndarray] = []

    @Slot()
    def run(self) -> None:
        started_at = time.monotonic()
        paused_total = 0.0
        pause_started: float | None = None

        try:
            self._output_path.parent.mkdir(parents=True, exist_ok=True)

            def callback(indata, frames, time_info, status) -> None:
                del frames, time_info
                if status:
                    pass
                if self._stop_event.is_set() or self._pause_event.is_set():
                    return

                chunk = np.asarray(indata[:, 0], dtype=np.float32).copy()
                self._frames.append(chunk)

                peak = float(np.max(np.abs(chunk))) if chunk.size else 0.0
                self.level_changed.emit(min(100, int(peak * 180)))

            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                device=self._device_index,
                callback=callback,
                blocksize=1600,
            ):
                while not self._stop_event.wait(0.20):
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
                        int(now - started_at - paused_total - active_pause),
                    )
                    self.elapsed_changed.emit(elapsed)

            if not self._frames:
                raise RuntimeError(
                    "NO SE CAPTURÓ AUDIO. REVISA EL MICRÓFONO Y SUS PERMISOS."
                )

            audio = np.concatenate(self._frames)
            pcm = np.clip(audio, -1.0, 1.0)
            pcm = (pcm * 32767.0).astype(np.int16)

            with wave.open(str(self._output_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self._sample_rate)
                wav.writeframes(pcm.tobytes())

            self.completed.emit(str(self._output_path))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def stop(self) -> None:
        self._stop_event.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._pause_event.set()
        else:
            self._pause_event.clear()
