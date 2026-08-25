from __future__ import annotations

import logging

from app.services.paths_service import AppPaths


def configure_logging() -> None:
    paths = AppPaths()
    paths.logs.mkdir(parents=True, exist_ok=True)
    log_file = paths.logs / "app.log"

    handlers = [
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )
