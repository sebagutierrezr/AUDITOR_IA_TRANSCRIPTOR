from __future__ import annotations

import os
import sys
from pathlib import Path


class AppPaths:
    """Rutas seguras para instalación Windows por usuario."""

    APP_DATA_FOLDER = "AUDITOR_IA_TRANSCRIPTOR"

    def __init__(self) -> None:
        if getattr(sys, "frozen", False):
            self.root = Path(sys.executable).resolve().parent
        else:
            self.root = Path(__file__).resolve().parents[2]

        # Activos incluidos con el instalador: solo lectura en ejecución.
        self.models = self.root / "models"
        self.resources = self.root / "resources"
        self.ffmpeg = self.root / "ffmpeg"

        # Datos que la aplicación necesita escribir.
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        else:
            base = Path.home() / ".local" / "share"

        self.user_root = base / self.APP_DATA_FOLDER
        self.temp = self.user_root / "temp"
        self.exports = self.user_root / "exports"
        self.logs = self.user_root / "logs"
        self.config = self.user_root / "config"
        self.data = self.user_root / "data"
        self.recordings = self.user_root / "recordings"

        for path in (
            self.user_root,
            self.temp,
            self.exports,
            self.logs,
            self.config,
            self.data,
            self.recordings,
        ):
            path.mkdir(parents=True, exist_ok=True)
