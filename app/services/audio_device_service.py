from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re
from typing import Any



@dataclass(frozen=True)
class InputDevice:
    index: int
    raw_name: str
    display_name: str
    sample_rate: int
    host_api: str = ""
    is_default: bool = False
    uid: str = ""
    channels: int = 1


@dataclass(frozen=True)
class OutputDevice:
    id: str
    raw_name: str
    display_name: str
    is_default: bool = False
    sample_rate: int = 48000
    channels: int = 2
    backend: str = "SOUNDCARD"
    backend_index: int | None = None

    @property
    def uid(self) -> str:
        return self.id


class AudioDeviceService:
    """Descubrimiento de audio sin depender de marcas ni nombres fijos.

    En Windows, el loopback de PyAudioWPatch es la primera opción porque expone
    el dispositivo WASAPI exacto. SoundCard queda como fallback automático.
    """

    logger = logging.getLogger(__name__)

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
        return value or "Dispositivo de audio"

    @classmethod
    def physical_key(cls, name: str) -> str:
        return re.sub(
            r"[^a-z0-9áéíóúüñ]+",
            " ",
            cls.clean_name(name).casefold(),
        ).strip()

    @staticmethod
    def _host_priority(host_name: str) -> int:
        host = str(host_name).casefold()
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
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            host_apis = sd.query_hostapis()
        except Exception as exc:
            cls.logger.warning("No se pudieron enumerar micrófonos: %s", exc)
            return []

        try:
            default_index = int(sd.default.device[0])
        except Exception:
            default_index = -1

        grouped: dict[str, tuple[int, InputDevice]] = {}
        for index, info in enumerate(devices):
            channels = int(info.get("max_input_channels", 0) or 0)
            if channels <= 0:
                continue
            raw_name = str(info.get("name", f"Micrófono {index}"))
            lowered = raw_name.casefold()
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

            key = cls.physical_key(raw_name) or f"input-{index}"
            priority = cls._host_priority(host_name) * 100
            if index == default_index:
                priority += 100000
            device = InputDevice(
                index=index,
                raw_name=raw_name,
                display_name=cls.clean_name(raw_name),
                sample_rate=max(8000, int(float(info.get("default_samplerate", 48000) or 48000))),
                host_api=host_name,
                is_default=index == default_index,
                uid=f"sd:{cls.physical_key(host_name)}:{key}",
                channels=max(1, min(channels, 2)),
            )
            current = grouped.get(key)
            if current is None or priority > current[0]:
                grouped[key] = (priority, device)

        result = [item[1] for item in grouped.values()]
        result.sort(key=lambda item: (not item.is_default, item.display_name.casefold()))
        return result

    @classmethod
    def _list_pawp_outputs(cls) -> list[OutputDevice]:
        if os.name != "nt":
            return []
        try:
            import pyaudiowpatch as pyaudio
        except Exception as exc:
            cls.logger.info("PyAudioWPatch no disponible: %s", exc)
            return []

        result: list[OutputDevice] = []
        try:
            with pyaudio.PyAudio() as p:
                try:
                    default = p.get_default_wasapi_loopback()
                    default_index = int(default.get("index", -1))
                except Exception:
                    default_index = -1
                for info in p.get_loopback_device_info_generator():
                    index = int(info.get("index", -1))
                    if index < 0:
                        continue
                    raw_name = str(info.get("name", f"Salida {index}"))
                    rate = int(float(info.get("defaultSampleRate", 48000) or 48000))
                    channels = int(info.get("maxInputChannels", 2) or 2)
                    key = cls.physical_key(raw_name) or f"output-{index}"
                    result.append(OutputDevice(
                        id=f"pawp:{key}",
                        raw_name=raw_name,
                        display_name=cls.clean_name(raw_name),
                        is_default=index == default_index,
                        sample_rate=max(8000, rate),
                        channels=max(1, min(channels, 2)),
                        backend="PYAUDIOWPATCH",
                        backend_index=index,
                    ))
        except Exception as exc:
            cls.logger.warning("WASAPI/PyAudioWPatch no pudo enumerarse: %s", exc)
            return []
        return result

    @classmethod
    def _list_soundcard_outputs(cls) -> list[OutputDevice]:
        try:
            import soundcard as sc
        except Exception as exc:
            cls.logger.info("SoundCard no disponible: %s", exc)
            return []
        try:
            default = sc.default_speaker()
            default_id = str(default.id) if default else ""
            speakers = sc.all_speakers()
        except Exception as exc:
            cls.logger.warning("SoundCard no pudo enumerar salidas: %s", exc)
            return []

        result = []
        for item in speakers:
            raw_name = str(item.name)
            item_id = str(item.id)
            key = cls.physical_key(raw_name) or item_id
            result.append(OutputDevice(
                id=f"soundcard:{key}",
                raw_name=raw_name,
                display_name=cls.clean_name(raw_name),
                is_default=item_id == default_id,
                sample_rate=48000,
                channels=1,
                backend="SOUNDCARD",
                backend_index=None,
            ))
        return result

    @classmethod
    def list_outputs(cls, backend_preference: str = "AUTO") -> list[OutputDevice]:
        preference = str(backend_preference or "AUTO").upper()
        pawp = cls._list_pawp_outputs() if preference in {"AUTO", "PYAUDIOWPATCH"} else []
        soundcard = cls._list_soundcard_outputs() if preference in {"AUTO", "SOUNDCARD"} else []

        if preference == "PYAUDIOWPATCH" and pawp:
            return sorted(pawp, key=lambda d: (not d.is_default, d.display_name.casefold()))
        if preference == "SOUNDCARD" and soundcard:
            return sorted(soundcard, key=lambda d: (not d.is_default, d.display_name.casefold()))

        # AUTO: conservar una opción por salida física. PyAudioWPatch tiene
        # prioridad; SoundCard se usa solo cuando WASAPI no expone esa salida.
        grouped: dict[str, OutputDevice] = {}
        for item in soundcard:
            grouped[cls.physical_key(item.raw_name)] = item
        for item in pawp:
            key = cls.physical_key(item.raw_name)
            current = grouped.get(key)
            if current is None or item.is_default or current.backend != "PYAUDIOWPATCH":
                grouped[key] = item

        result = list(grouped.values())
        result.sort(key=lambda d: (not d.is_default, d.display_name.casefold()))
        return result

    @classmethod
    def select_input(cls, devices: list[InputDevice], preferred_uid: str = "") -> InputDevice | None:
        if not devices:
            return None
        if preferred_uid:
            for item in devices:
                if item.uid == preferred_uid:
                    return item
        return next((item for item in devices if item.is_default), devices[0])

    @classmethod
    def select_output(cls, devices: list[OutputDevice], preferred_uid: str = "") -> OutputDevice | None:
        if not devices:
            return None
        if preferred_uid:
            for item in devices:
                if item.uid == preferred_uid:
                    return item
        return next((item for item in devices if item.is_default), devices[0])

    @classmethod
    def get_loopback(cls, output_id: str, output_name: str):
        """Compatibilidad para el backend SoundCard heredado."""
        try:
            import soundcard as sc
        except Exception as exc:
            raise RuntimeError(f"SoundCard no está disponible: {exc}") from exc

        raw_id = str(output_id or "")
        if raw_id.startswith("soundcard:"):
            raw_id = raw_id.split(":", 1)[1]
        loopbacks = [
            item for item in sc.all_microphones(include_loopback=True)
            if bool(getattr(item, "isloopback", False))
        ]
        target = " ".join(str(output_name or "").casefold().split())
        for item in loopbacks:
            if str(item.id) == raw_id:
                return item
        for item in loopbacks:
            current = " ".join(str(item.name).casefold().split())
            if current == target or current in target or target in current:
                return item
        target_words = {
            word for word in re.sub(r"[^a-z0-9áéíóúüñ]+", " ", target).split()
            if len(word) > 2
        }
        best: Any = None
        best_score = 0
        for item in loopbacks:
            current_words = set(re.sub(r"[^a-z0-9áéíóúüñ]+", " ", str(item.name).casefold()).split())
            score = len(target_words & current_words)
            if score > best_score:
                best, best_score = item, score
        if best is not None and best_score > 0:
            return best
        raise RuntimeError(
            "Windows no entregó una captura loopback para la salida seleccionada. "
            "Actualiza los dispositivos o elige otra salida de audio."
        )
