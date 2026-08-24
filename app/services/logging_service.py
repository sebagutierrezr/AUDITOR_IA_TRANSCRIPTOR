import logging

from app.services.paths_service import AppPaths


def configure_logging():
    path = AppPaths().logs / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8")],
    )
