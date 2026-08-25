from __future__ import annotations

import ast
import unittest
from pathlib import Path


class NonBlockingFileProcessingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_files_page_uses_qprocess(self):
        path = self.root / "app/ui/pages/files_page.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("QProcess", text)
        self.assertIn('"--file-worker"', text)
        self.assertNotIn("TranscriptionWorker(", text)

    def test_loading_file_does_not_open_or_stat_audio(self):
        path = self.root / "app/ui/pages/files_page.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        load_method = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_load_file":
                load_method = node
                break
        self.assertIsNotNone(load_method)
        source = ast.unparse(load_method)
        for item in (
            ".stat(",
            "av.open(",
            "torchaudio",
            "WhisperModel",
            "DiarizationService",
            "SpeakerRescueService",
        ):
            self.assertNotIn(item, source)

    def test_file_worker_protocol_exists(self):
        path = self.root / "app/file_worker_cli.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('EVENT_PREFIX = "AUDITOR_EVENT|"', text)
        self.assertIn("DiarizationService", text)
        self.assertIn("FasterWhisperEngine", text)


if __name__ == "__main__":
    unittest.main()
