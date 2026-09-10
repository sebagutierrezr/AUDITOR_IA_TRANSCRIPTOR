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
        self.completed.emit(
            "Micrófono disponible, pero no se detectó voz durante la prueba."
            if maximum < 0.001
            else "Micrófono listo para transcribir."
        )

    def test_client(self) -> None:
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            raise RuntimeError("No se pudo cargar WASAPI loopback.") from exc

        index = AudioDeviceService.loopback_index(self.output_id)
        maximum = 0.0
        started = time.monotonic()

        with pyaudio.PyAudio() as manager:
            info = manager.get_device_info_by_index(index)
            rate = int(float(info.get("defaultSampleRate", 48000)))
            channels = max(1, min(2, int(info.get("maxInputChannels", 2) or 2)))
            block = max(1024, int(rate * 0.08))
            with manager.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=index,
                frames_per_buffer=block,
            ) as stream:
                while time.monotonic() - started < 3.0:
                    raw = stream.read(block, exception_on_overflow=False)
                    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    if channels > 1 and samples.size >= channels:
                        samples = samples[: samples.size - (samples.size % channels)].reshape(-1, channels).mean(axis=1)
                    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
                    maximum = max(maximum, peak)
                    self.level_changed.emit(max(0, min(100, int(peak / 0.20 * 100))))

        self.completed.emit(
            "Salida disponible, pero no se reprodujo audio durante la prueba."
            if maximum < 0.002
            else "Audio del cliente listo para transcribir."
        )
