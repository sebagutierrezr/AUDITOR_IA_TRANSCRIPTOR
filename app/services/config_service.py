import json
import logging

from app.models.settings import AppSettings
from app.services.paths_service import AppPaths


class ConfigService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.path = AppPaths().config / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if not self.path.exists():
            settings = AppSettings()
            self.save(settings)
            return settings
        try:
            return AppSettings.from_dict(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except Exception:
            self.logger.exception("ERROR AL LEER CONFIGURACION")
            settings = AppSettings()
            self.save(settings)
            return settings

    def save(self, settings):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.path)
