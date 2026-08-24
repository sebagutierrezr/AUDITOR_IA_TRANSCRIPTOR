from __future__ import annotations

import os
import sys
from pathlib import Path


class AppPaths:
    APP_FOLDER = "AUDITOR_IA_TRANSCRIPTOR"

    def __init__(self) -> None:
        if getattr(sys, "frozen", False):
            self.root = Path(sys.executable).resolve().parent
        else:
            self.root = Path(__file__).resolve().parents[2]

        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        else:
            base = Path.home() / ".local" / "share"

        self.user_root = base / self.APP_FOLDER
        self.config = self.user_root / "config"
        self.data = self.user_root / "data"
        self.exports = self.user_root / "exports"
        self.logs = self.user_root / "logs"
        self.references = self.user_root / "references"

        for path in (
            self.config,
            self.data,
            self.exports,
            self.logs,
            self.references,
        ):
            path.mkdir(parents=True, exist_ok=True)
