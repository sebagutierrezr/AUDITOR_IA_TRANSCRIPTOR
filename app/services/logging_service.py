import logging
from pathlib import Path

def configure_logging():
    base = Path(__file__).resolve().parents[2]
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", handlers=[logging.FileHandler(log_dir / "app.log", encoding="utf-8"), logging.StreamHandler()], force=True)
