from __future__ import annotations

import time

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot

from app.services.audio_device_service import AudioDeviceService


class AudioTestWorker(QObject):
    level_changed = Signal(int)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        mode: str,
        input_index: int | None = None,
        input_rate: int = 48000,
        output_id: str = "",
        output_name: str = "",
    ) -> None:
        super().__init__()
        self.mode = mode
        self.input_index = input_index
        self.input_rate = input_rate
        self.output_id = output_id
        self.output_name = output_name

    @Slot()
    def run(self) -> None:
        try:
            if self.mode == "agent":
                self.test_agent()
            else:
                self.test_client()
        except Exception as exc:
            detail = str(exc).strip() or repr(exc).strip() or exc.__class__.__name__
            self.failed.emit(detail)
        finally:
            self.finished.emit()

    def test_agent(self) -> None:
        if self.input_index is None:
            raise RuntimeError("No hay un micrófono seleccionado.")
        rate = int(self.input_rate or 48000)
        block = max(512, int(rate * 0.08))
        maximum = 0.0
        started = time.monotonic()
        with sd.InputStream(
            samplerate=rate,
            channels=1,
            dtype="float32",
            device=self.input_index,
            blocksize=block,
            latency="high",
        ) as stream:
            while time.monotonic() - started < 3.0:
                data, _ = stream.read(block)
                audio = np.asarray(data[:, 0], dtype=np.float32)
                peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                maximum = max(maximum, peak)
                self.level_changed.emit(max(0, min(100, int(peak / 0.035 * 100))))
        if maximum < 0.001:
            self.completed.emit("Micrófono disponible, pero no se detectó voz durante la prueba.")
        else:
            self.completed.emit("Micrófono listo para transcribir.")

    def test_client(self) -> None:
        loopback = AudioDeviceService.get_loopback(self.output_id, self.output_name)
        maximum = 0.0
        started = time.monotonic()
        with loopback.recorder(samplerate=48000, channels=1, blocksize=3840) as recorder:
            while time.monotonic() - started < 3.0:
                audio = np.asarray(recorder.record(numframes=3840), dtype=np.float32).reshape(-1)
                peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                maximum = max(maximum, peak)
                self.level_changed.emit(max(0, min(100, int(peak / 0.20 * 100))))
        if maximum < 0.002:
            self.completed.emit("Salida disponible, pero no se reprodujo audio durante la prueba.")
        else:
            self.completed.emit("Audio del cliente listo para transcribir.")
