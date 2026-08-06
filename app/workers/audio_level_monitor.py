import threading
import time

import numpy as np
import soundcard as sc
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot


class AudioLevelMonitor(QObject):
    agent_level_changed = Signal(int)
    client_level_changed = Signal(int)
    source_warning = Signal(str)
    finished = Signal()

    def __init__(
        self,
        monitor_agent: bool,
        monitor_client: bool,
        agent_device_index: int | None,
        client_loopback_id: str | None,
        client_loopback_name: str | None,
    ) -> None:
        super().__init__()

        self._monitor_agent = monitor_agent
        self._monitor_client = monitor_client
        self._agent_device_index = agent_device_index
        self._client_loopback_id = client_loopback_id
        self._client_loopback_name = client_loopback_name

        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def stop(self) -> None:
        self._stop_event.set()

    @Slot()
    def run(self) -> None:
        try:
            if (
                self._monitor_agent
                and self._agent_device_index is not None
            ):
                agent_thread = threading.Thread(
                    target=self._monitor_agent_level,
                    daemon=True,
                )
                self._threads.append(agent_thread)
                agent_thread.start()

            if self._monitor_client:
                client_thread = threading.Thread(
                    target=self._monitor_client_level,
                    daemon=True,
                )
                self._threads.append(client_thread)
                client_thread.start()

            while (
                not self._stop_event.is_set()
                and any(
                    thread.is_alive()
                    for thread in self._threads
                )
            ):
                time.sleep(0.05)

        finally:
            self._stop_event.set()

            for thread in self._threads:
                thread.join(timeout=1.0)

            self.finished.emit()

    def _monitor_agent_level(self) -> None:
        try:
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
                int(sample_rate * 0.08),
            )

            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                device=self._agent_device_index,
                blocksize=blocksize,
                latency="high",
            ) as stream:
                while not self._stop_event.is_set():
                    data, _ = stream.read(blocksize)

                    frame = np.asarray(
                        data[:, 0],
                        dtype=np.float32,
                    )
                    peak = (
                        float(np.max(np.abs(frame)))
                        if frame.size
                        else 0.0
                    )

                    self.agent_level_changed.emit(
                        min(
                            100,
                            int(peak * 2500),
                        )
                    )

        except Exception as exc:
            if not self._stop_event.is_set():
                self.source_warning.emit(
                    f"MICRÓFONO: {exc}"
                )

    def _monitor_client_level(self) -> None:
        try:
            loopback = self._find_loopback()
            sample_rate = 48000
            blocksize = 2400

            with loopback.recorder(
                samplerate=sample_rate,
                channels=1,
                blocksize=blocksize,
            ) as recorder:
                while not self._stop_event.is_set():
                    data = recorder.record(
                        numframes=blocksize
                    )

                    frame = np.asarray(
                        data,
                        dtype=np.float32,
                    ).reshape(-1)
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

        except Exception as exc:
            if not self._stop_event.is_set():
                self.source_warning.emit(
                    f"AUDIO DEL PC: {exc}"
                )

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
            "NO SE ENCONTRÓ LA SALIDA SELECCIONADA."
        )
