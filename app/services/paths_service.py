from __future__ import annotations

import sys
from pathlib import Path


class AppPaths:
    def __init__(self) -> None:
        if getattr(sys, "frozen", False):
            self.root = Path(sys.executable).resolve().parent
        else:
            self.root = Path(__file__).resolve().parents[2]

        self.models = self.root / "models"
        self.engines = self.root / "engines"
        self.temp = self.root / "temp"
        self.exports = self.root / "exports"
        self.logs = self.root / "logs"
        self.recordings = self.root / "recordings"
        self.config = self.root / "config"
        self.data = self.root / "data"

        for path in (
            self.models,
            self.engines,
            self.temp,
            self.exports,
            self.logs,
            self.recordings,
            self.config,
            self.data,
        ):
            path.mkdir(parents=True, exist_ok=True)
