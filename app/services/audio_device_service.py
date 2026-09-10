from __future__ import annotations

from dataclasses import dataclass
import re

import sounddevice as sd


@dataclass(frozen=True)
class InputDevice:
    index: int
    raw_name: str
    display_name: str
    sample_rate: int
    host_api: str = ""
    is_default: bool = False


@dataclass(frozen=True)
class OutputDevice:
    id: str
    raw_name: str
    display_name: str
    is_default: bool = False
    sample_rate: int = 48000
    channels: int = 2


class AudioDeviceService:
    """Enumera micrófonos y loopbacks WASAPI de forma estable en Windows."""

    BRAND_REPLACEMENTS = {
        "logi": "Logitech",
        "realtek(r) audio": "Realtek Audio",
        "nvidia high definition audio": "NVIDIA Audio",
    }

    @classmethod
    def clean_name(cls, name: str) -> str:
        value = str(name or "").strip()
        value = re.sub(
            r"^(micrófono|microfono|microphone|altavoces|speakers|headphones|auriculares)\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"^\(?\d+\s*-\s*", "", value)
        value = re.sub(r"\s*\[loopback\]\s*$", "", value, flags=re.IGNORECASE)
        value = value.strip(" ()")
        lowered = value.lower()
        for source, target in cls.BRAND_REPLACEMENTS.items():
            if source in lowered:
                value = re.sub(re.escape(source), target, value, flags=re.IGNORECASE)
                break
        return value or "Dispositivo de audio"

    @classmethod
    def physical_key(cls, name: str) -> str:
        return re.sub(
            r"[^a-z0-9áéíóúüñ]+",
            " ",
            cls.clean_name(name).lower(),
        ).strip()

    @staticmethod
    def _host_priority(host_name: str) -> int:
        host = str(host_name).lower()
        if "wasapi" in host:
            return 50
        if "wdm-ks" in host:
            return 40
        if "directsound" in host:
            return 30
        if "mme" in host:
            return 20
        return 10

    @classmethod
    def list_inputs(cls) -> list[InputDevice]:
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()
        try:
            default_index = int(sd.default.device[0])
        except Exception:
            default_index = -1

        default_physical_key = ""
        if 0 <= default_index < len(devices):
            default_physical_key = cls.physical_key(str(devices[default_index].get("name", "")))

        grouped: dict[str, tuple[int, InputDevice]] = {}
        for index, info in enumerate(devices):
            if int(info.get("max_input_channels", 0)) <= 0:
                continue

            raw_name = str(info.get("name", f"Micrófono {index}"))
            lowered = raw_name.lower()
            if any(token in lowered for token in (
                "microsoft sound mapper",
                "asignador de sonido microsoft",
                "primary sound capture",
                "controlador primario de captura",
            )):
                continue

            host_name = ""
            try:
                host_name = str(host_apis[int(info.get("hostapi", -1))]["name"])
            except Exception:
                pass

            physical_key = cls.physical_key(raw_name)
            is_default_physical = bool(default_physical_key) and physical_key == default_physical_key
            priority = 100000 if index == default_index else cls._host_priority(host_name) * 100
            device = InputDevice(
                index=index,
                raw_name=raw_name,
                display_name=cls.clean_name(raw_name),
                sample_rate=int(float(info.get("default_samplerate", 48000))),
                host_api=host_name,
                is_default=is_default_physical,
            )
            current = grouped.get(physical_key)
            if current is None or priority > current[0]:
                grouped[physical_key] = (priority, device)

        result = [item[1] for item in grouped.values()]
        result.sort(key=lambda item: (not item.is_default, item.display_name.lower()))
        return result

    @classmethod
    def list_outputs(cls) -> list[OutputDevice]:
        """Devuelve directamente dispositivos de entrada WASAPI loopback.

        PyAudioWPatch expone los loopbacks como dispositivos de entrada; esto
        evita depender de coincidencias frágiles entre IDs de altavoz y micrófono.
        """
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            raise RuntimeError(
                "El componente WASAPI de audio no está disponible. Reinstala AUDITOR IA 8.0.1."
            ) from exc

        result: list[OutputDevice] = []
        with pyaudio.PyAudio() as manager:
            default_index = -1
            try:
                default_index = int(manager.get_default_wasapi_loopback()["index"])
            except Exception:
                pass

            grouped: dict[str, OutputDevice] = {}
            for info in manager.get_loopback_device_info_generator():
                index = int(info.get("index", -1))
                if index < 0:
                    continue
                raw_name = str(info.get("name", f"Salida {index}"))
                key = cls.physical_key(raw_name)
                device = OutputDevice(
                    id=str(index),
                    raw_name=raw_name,
                    display_name=cls.clean_name(raw_name),
                    is_default=index == default_index,
                    sample_rate=int(float(info.get("defaultSampleRate", 48000))),
                    channels=max(1, min(2, int(info.get("maxInputChannels", 2) or 2))),
                )
                current = grouped.get(key)
                if current is None or (device.is_default and not current.is_default):
                    grouped[key] = device
            result = list(grouped.values())

        result.sort(key=lambda item: (not item.is_default, item.display_name.lower()))
        return result

    @staticmethod
    def loopback_index(output_id: str) -> int:
        try:
            return int(str(output_id).strip())
        except Exception as exc:
            raise RuntimeError("La salida de audio seleccionada ya no es válida.") from exc
