from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import subprocess

import psutil


@dataclass(frozen=True)
class RuntimeTuning:
    profile: str
    cpu_threads: int
    live_beam_size: int
    file_beam_size: int
    live_max_phrase_seconds: float
    live_queue_limit: int
    description: str


@dataclass(frozen=True)
class SystemProfile:
    os_name: str
    os_release: str
    architecture: str
    logical_cores: int
    physical_cores: int
    ram_gb: float
    nvidia_gpu: bool
    tuning: RuntimeTuning


class SystemProfileService:
    """Detecta recursos del equipo y elige una carga segura.

    La aplicación siempre usa CPU como base. La GPU solo se informa y puede
    usarse en futuras aceleraciones; nunca es un requisito para iniciar.
    """

    @staticmethod
    def _has_nvidia_gpu() -> bool:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    @classmethod
    def detect(cls, requested: str = "AUTO") -> SystemProfile:
        logical = max(1, int(os.cpu_count() or 1))
        physical = max(1, int(psutil.cpu_count(logical=False) or max(1, logical // 2)))
        ram_gb = float(psutil.virtual_memory().total) / (1024 ** 3)
        normalized = str(requested or "AUTO").strip().upper()

        if normalized == "AUTO":
            if ram_gb < 7.5 or physical <= 2:
                normalized = "ECO"
            elif ram_gb >= 15.0 and physical >= 6:
                normalized = "CALIDAD"
            else:
                normalized = "BALANCEADO"

        if normalized == "ECO":
            tuning = RuntimeTuning(
                profile="ECO",
                cpu_threads=max(1, min(2, logical - 1 if logical > 1 else 1)),
                live_beam_size=1,
                file_beam_size=2,
                live_max_phrase_seconds=8.0,
                live_queue_limit=12,
                description="Prioriza estabilidad y bajo consumo.",
            )
        elif normalized == "CALIDAD":
            tuning = RuntimeTuning(
                profile="CALIDAD",
                cpu_threads=max(2, min(6, logical - 2 if logical > 3 else logical)),
                live_beam_size=4,
                file_beam_size=5,
                live_max_phrase_seconds=12.0,
                live_queue_limit=24,
                description="Prioriza precisión en equipos con más recursos.",
            )
        else:
            tuning = RuntimeTuning(
                profile="BALANCEADO",
                cpu_threads=max(2, min(4, logical - 2 if logical > 3 else logical)),
                live_beam_size=3,
                file_beam_size=3,
                live_max_phrase_seconds=10.0,
                live_queue_limit=18,
                description="Equilibrio entre precisión, latencia y consumo.",
            )

        return SystemProfile(
            os_name=platform.system(),
            os_release=platform.release(),
            architecture=platform.machine(),
            logical_cores=logical,
            physical_cores=physical,
            ram_gb=ram_gb,
            nvidia_gpu=cls._has_nvidia_gpu(),
            tuning=tuning,
        )
