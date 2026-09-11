from __future__ import annotations

import queue
import threading
from typing import Protocol

import numpy as np

from app.services.audio_device_service import AudioDeviceService, OutputDevice


class LoopbackReader(Protocol):
    sample_rate: int
    channels: int
    def __enter__(self): ...
    def __exit__(self, exc_type, exc, tb): ...
    def read(self, timeout: float = 0.25) -> np.ndarray: ...


class PyAudioWPatchLoopback:
    """Captura WASAPI por callback para que STOP nunca dependa de stream.read()."""

    def __init__(self, device: OutputDevice, frames_per_buffer: int = 2048) -> None:
        self.device = device
        self.sample_rate = int(device.sample_rate or 48000)
        self.channels = max(1, min(int(device.channels or 2), 2))
        self.frames_per_buffer = frames_per_buffer
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=64)
        self._manager = None
        self._stream = None
        self._closed = threading.Event()

    def __enter__(self):
        import pyaudiowpatch as pyaudio
        if self.device.backend_index is None:
            raise RuntimeError("La salida WASAPI no tiene índice de captura.")
        self._manager = pyaudio.PyAudio()

        def callback(in_data, frame_count, time_info, status):
            if self._closed.is_set():
                return (None, pyaudio.paComplete)
            if in_data:
                try:
                    self._queue.put_nowait(in_data)
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._queue.put_nowait(in_data)
                    except queue.Full:
                        pass
            return (None, pyaudio.paContinue)

        self._stream = self._manager.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            frames_per_buffer=self.frames_per_buffer,
            input=True,
            input_device_index=int(self.device.backend_index),
            stream_callback=callback,
        )
        self._stream.start_stream()
        return self

    def read(self, timeout: float = 0.25) -> np.ndarray:
        try:
            data = self._queue.get(timeout=max(0.02, timeout))
        except queue.Empty:
            return np.array([], dtype=np.float32)
        raw = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        if self.channels > 1 and raw.size >= self.channels:
            raw = raw[: (raw.size // self.channels) * self.channels]
            raw = raw.reshape(-1, self.channels).mean(axis=1)
        return np.asarray(raw, dtype=np.float32).reshape(-1)

    def __exit__(self, exc_type, exc, tb):
        self._closed.set()
        try:
            if self._stream is not None:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
        finally:
            self._stream = None
            if self._manager is not None:
                self._manager.terminate()
                self._manager = None
        return False


class SoundCardLoopback:
    def __init__(self, device: OutputDevice, blocksize: int = 2048) -> None:
        self.device = device
        self.sample_rate = int(device.sample_rate or 48000)
        self.channels = 1
        self.blocksize = blocksize
        self._recorder = None
        self._context = None

    def __enter__(self):
        loopback = AudioDeviceService.get_loopback(self.device.id, self.device.raw_name)
        self._context = loopback.recorder(
            samplerate=self.sample_rate,
            channels=1,
            blocksize=self.blocksize,
        )
        self._recorder = self._context.__enter__()
        return self

    def read(self, timeout: float = 0.25) -> np.ndarray:
        # SoundCard no expone timeout. Usamos bloques cortos para que detener
        # siga siendo responsivo incluso en el fallback.
        data = self._recorder.record(numframes=self.blocksize)
        return np.asarray(data, dtype=np.float32).reshape(-1)

    def __exit__(self, exc_type, exc, tb):
        if self._context is not None:
            try:
                self._context.__exit__(exc_type, exc, tb)
            finally:
                self._context = None
                self._recorder = None
        return False


class LoopbackCaptureFactory:
    @staticmethod
    def create(device: OutputDevice) -> LoopbackReader:
        backend = str(device.backend or "").upper()
        if backend == "PYAUDIOWPATCH":
            return PyAudioWPatchLoopback(device)
        if backend == "SOUNDCARD":
            return SoundCardLoopback(device)
        raise RuntimeError(f"Backend de audio no compatible: {device.backend}")
