from __future__ import annotations

import time

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot

from app.services.audio_capture_backend import LoopbackCaptureFactory
from app.services.audio_device_service import OutputDevice


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
        output_backend: str = "SOUNDCARD",
        output_backend_index: int | None = None,
        output_rate: int = 48000,
        output_channels: int = 2,
    ) -> None:
        super().__init__()
        self.mode = mode
        self.input_index = input_index
        self.input_rate = input_rate
        self.output_device = OutputDevice(
            id=output_id,
            raw_name=output_name,
            display_name=output_name,
            backend=output_backend,
            backend_index=output_backend_index,
            sample_rate=int(output_rate or 48000),
            channels=max(1, int(output_channels or 1)),
        )

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
        self.completed.emit(
            "Micrófono disponible, pero no se detectó voz durante la prueba."
            if maximum < 0.001
            else "Micrófono listo para transcribir."
        )

    def test_client(self) -> None:
        maximum = 0.0
        started = time.monotonic()
        with LoopbackCaptureFactory.create(self.output_device) as reader:
            while time.monotonic() - started < 3.0:
                audio = reader.read(timeout=0.20)
                if audio.size == 0:
                    continue
                peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                maximum = max(maximum, peak)
                self.level_changed.emit(max(0, min(100, int(peak / 0.20 * 100))))
        self.completed.emit(
            "Salida disponible, pero no se reprodujo audio durante la prueba."
            if maximum < 0.002
            else "Audio del cliente listo para transcribir."
        )
