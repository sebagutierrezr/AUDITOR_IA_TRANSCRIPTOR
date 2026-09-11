from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import subprocess

from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.services.audio_device_service import AudioDeviceService
from app.services.nemo_diarization_service import NemoDiarizationService
from app.services.paths_service import AppPaths
from app.services.system_profile_service import SystemProfileService


@dataclass(frozen=True)
class DiagnosticItem:
    name: str
    ok: bool
    detail: str
    warning: bool = False


class DiagnosticService:
    def __init__(self, performance_mode: str = "AUTO", audio_backend: str = "AUTO") -> None:
        self.performance_mode = performance_mode
        self.audio_backend = audio_backend
        self.paths = AppPaths()

    def run_quick(self) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        profile = SystemProfileService.detect(self.performance_mode)
        is_windows = os.name == "nt"
        is_64 = "64" in platform.architecture()[0] or "64" in profile.architecture
        items.append(DiagnosticItem(
            "Windows 64 bits",
            is_windows and is_64,
            f"{platform.system()} {platform.release()} · {profile.architecture}",
            warning=not is_windows,
        ))
        items.append(DiagnosticItem(
            "Hardware",
            profile.ram_gb >= 6 and profile.logical_cores >= 4,
            f"{profile.physical_cores} núcleos físicos / {profile.logical_cores} lógicos · "
            f"{profile.ram_gb:.1f} GB RAM · perfil {profile.tuning.profile}",
            warning=profile.ram_gb < 8,
        ))

        try:
            probe = self.paths.temp / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            items.append(DiagnosticItem("Carpetas de usuario", True, str(self.paths.user_root)))
        except Exception as exc:
            items.append(DiagnosticItem("Carpetas de usuario", False, str(exc)))

        whisper_engine = FasterWhisperEngine("ALTA", self.performance_mode)
        whisper = whisper_engine.is_ready()
        model_label = whisper_engine.model_name.capitalize()
        items.append(DiagnosticItem(
            "Motor de transcripción",
            whisper,
            f"Faster-Whisper {model_label} local" if whisper else f"Modelo {model_label} incompleto",
        ))
        diar = NemoDiarizationService().is_ready()
        items.append(DiagnosticItem(
            "Separación de hablantes",
            diar,
            "SortFormer local" if diar else "SortFormer/NeMo incompleto",
            warning=not diar,
        ))

        ffmpeg = self.paths.ffmpeg / "bin" / "ffmpeg.exe"
        items.append(DiagnosticItem(
            "FFmpeg",
            ffmpeg.is_file(),
            str(ffmpeg) if ffmpeg.is_file() else "No encontrado dentro de la aplicación",
        ))

        try:
            inputs = AudioDeviceService.list_inputs()
            outputs = AudioDeviceService.list_outputs(self.audio_backend)
            backends = ", ".join(sorted({item.backend for item in outputs})) or "ninguno"
            items.append(DiagnosticItem(
                "Micrófonos",
                bool(inputs),
                f"{len(inputs)} dispositivo(s) detectado(s)",
            ))
            items.append(DiagnosticItem(
                "Audio del PC / loopback",
                bool(outputs),
                f"{len(outputs)} salida(s) · backend: {backends}",
            ))
        except Exception as exc:
            items.append(DiagnosticItem("Audio de Windows", False, str(exc)))

        return items
