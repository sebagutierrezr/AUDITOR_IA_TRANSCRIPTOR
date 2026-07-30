import json, logging
from pathlib import Path
from app.models.settings import AppSettings

class ConfigService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.path = Path(__file__).resolve().parents[2] / "config" / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def load(self):
        if not self.path.exists():
            s=AppSettings(); self.save(s); return s
        try: return AppSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            self.logger.exception("ERROR AL LEER CONFIGURACION")
            s=AppSettings(); self.save(s); return s
    def save(self, settings):
        temp=self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)
