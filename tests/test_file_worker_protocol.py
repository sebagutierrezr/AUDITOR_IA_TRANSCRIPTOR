from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.file_worker_cli import Progress


class FileWorkerProtocolTests(unittest.TestCase):
    def test_progress_uses_json_file_not_stdout(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            progress = Progress(path)
            progress(25, "TRANSCRIBIENDO")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["type"], "progress")
            self.assertEqual(payload["value"], 25)
            self.assertEqual(payload["message"], "TRANSCRIBIENDO")

    def test_completed_contains_result_path_and_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            result = Path(folder) / "result.json"
            progress = Progress(path)
            progress.completed(result, "respaldo contextual")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["type"], "completed")
            self.assertEqual(payload["result_path"], str(result))
            self.assertIn("respaldo", payload["warning"])

    def test_failed_is_visible_to_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            progress = Progress(path)
            progress.failed(RuntimeError("FALLO CONTROLADO"))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["type"], "failed")
            self.assertEqual(payload["error_type"], "RuntimeError")
            self.assertIn("FALLO CONTROLADO", payload["message"])


if __name__ == "__main__":
    unittest.main()
