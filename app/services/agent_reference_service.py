from __future__ import annotations

import shutil
from pathlib import Path

from app.services.paths_service import AppPaths


class AgentReferenceService:
    SUPPORTED = {
        ".mp3",
        ".mp4",
        ".mpeg",
        ".mpga",
        ".m4a",
        ".ogg",
        ".wav",
        ".webm",
    }

    def __init__(self) -> None:
        self.paths = AppPaths()

    def save_reference(self, source: Path) -> Path:
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in self.SUPPORTED:
            raise ValueError("Formato de muestra de voz no compatible.")
        if source.stat().st_size > 8 * 1024 * 1024:
            raise ValueError(
                "La muestra es demasiado grande. Usa un fragmento limpio de 2 a 10 segundos."
            )
        for old in self.paths.references.glob("agent_reference.*"):
            old.unlink(missing_ok=True)
        target = self.paths.references / f"agent_reference{source.suffix.lower()}"
        shutil.copy2(source, target)
        return target

    def delete_reference(self) -> None:
        for old in self.paths.references.glob("agent_reference.*"):
            old.unlink(missing_ok=True)
