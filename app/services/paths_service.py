from __future__ import annotations

import os
import sys
from pathlib import Path


class AppPaths:
    """Rutas de la aplicacion y datos de usuario.

    ``root`` apunta siempre al directorio del ejecutable instalado.
    ``bundle_root`` apunta al directorio real de recursos de PyInstaller
    (sys._MEIPASS) cuando corresponde. Asi funciona tanto con layout plano
    como con ``_internal``.
    """

    APP_DATA_FOLDER = "AUDITOR_IA_TRANSCRIPTOR"

    def __init__(self) -> None:
        if getattr(sys, "frozen", False):
            self.root = Path(sys.executable).resolve().parent
            self.bundle_root = Path(
                getattr(sys, "_MEIPASS", self.root)
            ).resolve()
        else:
            self.root = Path(__file__).resolve().parents[2]
            self.bundle_root = self.root

        # Activos incluidos con el instalador: solo lectura en ejecucion.
        self.models = self.bundle_root / "models"
        self.resources = self.bundle_root / "resources"
        self.ffmpeg = self.bundle_root / "ffmpeg"
        self.nemo_speech = self.bundle_root / "nemo-speech"

        # Datos que la aplicacion necesita escribir.
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
