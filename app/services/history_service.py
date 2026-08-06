import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.services.paths_service import AppPaths


class HistoryService:
    def __init__(self) -> None:
        self._path = AppPaths().data / "transcription_history.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(__name__)

    def list_entries(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                return []
            return sorted(
                payload,
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )
        except Exception:
            self._logger.exception("ERROR LEYENDO HISTORIAL")
            return []

    def add_entry(
        self,
        source_path: str,
        text: str,
        profile: str,
        language: str,
    ) -> dict:
        entries = self.list_entries()
        entry = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source_path": source_path,
            "source_name": Path(source_path).name,
            "profile": profile,
            "language": language,
            "text": text,
        }
        entries.insert(0, entry)
        self._write(entries[:200])
        return entry

    def update_text(self, entry_id: str, text: str) -> None:
        entries = self.list_entries()
        changed = False
        for entry in entries:
            if entry.get("id") == entry_id:
                entry["text"] = text
                entry["updated_at"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                changed = True
                break
        if changed:
            self._write(entries)

    def delete_entry(self, entry_id: str) -> None:
        entries = [
            entry
            for entry in self.list_entries()
            if entry.get("id") != entry_id
        ]
        self._write(entries)

    def clear(self) -> None:
        self._write([])

    def _write(self, entries: list[dict]) -> None:
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)
