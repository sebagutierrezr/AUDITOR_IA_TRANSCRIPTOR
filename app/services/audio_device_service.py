from __future__ import annotations

from dataclasses import dataclass
import re

import soundcard as sc
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


class AudioDeviceService:
    """Enumera dispositivos sin abrirlos ni modificar Windows."""

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
        """
        Devuelve una sola entrada por dispositivo físico.

        El índice exacto que Windows tiene como predeterminado se conserva.
        No se reemplaza silenciosamente por otra variante WASAPI/MME del mismo
        dispositivo físico, porque eso puede abrir una entrada sin señal.
        """
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()
        default_index = int(sd.default.device[0])

        default_physical_key = ""
        if 0 <= default_index < len(devices):
            default_physical_key = cls.physical_key(
                str(devices[default_index].get("name", ""))
            )

        grouped: dict[str, tuple[int, InputDevice]] = {}

        for index, info in enumerate(devices):
            if int(info.get("max_input_channels", 0)) <= 0:
                continue

            raw_name = str(info.get("name", f"Micrófono {index}"))
            lowered = raw_name.lower()

            if any(
                token in lowered
                for token in (
                    "microsoft sound mapper",
                    "asignador de sonido microsoft",
                    "primary sound capture",
                    "controlador primario de captura",
                )
            ):
                continue

            host_name = ""
            try:
                host_name = str(
                    host_apis[int(info.get("hostapi", -1))]["name"]
                )
            except Exception:
                pass

            physical_key = cls.physical_key(raw_name)
            is_default_physical = (
                bool(default_physical_key)
                and physical_key == default_physical_key
            )

            # El índice predeterminado exacto de Windows tiene prioridad
            # absoluta. Solo si no es el predeterminado se usa la prioridad
            # del backend como criterio secundario.
            priority = (
                100000
                if index == default_index
                else cls._host_priority(host_name) * 100
            )

            device = InputDevice(
                index=index,
                raw_name=raw_name,
                display_name=cls.clean_name(raw_name),
                sample_rate=int(
                    float(info.get("default_samplerate", 48000))
                ),
                host_api=host_name,
                is_default=is_default_physical,
            )

            current = grouped.get(physical_key)
            if current is None or priority > current[0]:
                grouped[physical_key] = (priority, device)

        result = [item[1] for item in grouped.values()]
        result.sort(
            key=lambda item: (
                not item.is_default,
                item.display_name.lower(),
            )
        )
        return result

    @classmethod
    def list_outputs(cls) -> list[OutputDevice]:
        try:
            default = sc.default_speaker()
            default_id = str(default.id) if default else ""
        except Exception:
            default_id = ""

        grouped: dict[str, OutputDevice] = {}
        for item in sc.all_speakers():
            raw_name = str(item.name)
            key = cls.physical_key(raw_name)
            device = OutputDevice(
                id=str(item.id),
                raw_name=raw_name,
                display_name=cls.clean_name(raw_name),
                is_default=str(item.id) == default_id,
            )
            current = grouped.get(key)
            if current is None or (device.is_default and not current.is_default):
                grouped[key] = device

        result = list(grouped.values())
        result.sort(key=lambda item: (not item.is_default, item.display_name.lower()))
        return result

    @staticmethod
    def get_loopback(output_id: str, output_name: str):
        loopbacks = [
            item
            for item in sc.all_microphones(include_loopback=True)
            if bool(getattr(item, "isloopback", False))
        ]
        target = " ".join(str(output_name or "").lower().split())

        # Algunos controladores comparten ID; otros solamente el nombre físico.
        for item in loopbacks:
            if str(item.id) == str(output_id):
                return item

        for item in loopbacks:
            current = " ".join(str(item.name).lower().split())
            if current == target or current in target or target in current:
                return item

        target_words = {
            word
            for word in re.sub(r"[^a-z0-9áéíóúüñ]+", " ", target).split()
            if len(word) > 2
        }
        best = None
        best_score = 0
        for item in loopbacks:
            current_words = set(
                re.sub(r"[^a-z0-9áéíóúüñ]+", " ", str(item.name).lower()).split()
            )
            score = len(target_words & current_words)
            if score > best_score:
                best, best_score = item, score
        if best is not None and best_score > 0:
            return best
        raise RuntimeError("No fue posible asociar la salida seleccionada con su captura de audio.")
