from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.services.paths_service import AppPaths


def configure_logging() -> None:
    paths = AppPaths()
    paths.logs.mkdir(parents=True, exist_ok=True)
    log_file = paths.logs / "app.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=4,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
        force=True,
    )
