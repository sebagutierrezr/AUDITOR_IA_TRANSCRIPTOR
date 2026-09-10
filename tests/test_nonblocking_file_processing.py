from __future__ import annotations

import ast
import unittest
from pathlib import Path


class NonBlockingFileProcessingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_files_page_uses_isolated_qprocess_and_json_progress(self):
        text = (self.root / "app/ui/pages/files_page.py").read_text(encoding="utf-8")
        self.assertIn("QProcess", text)
        self.assertIn('"--file-worker"', text)
        self.assertIn('f"progress_{job_id}.json"', text)
        self.assertIn("QProcess.nullDevice()", text)
        self.assertIn("_poll_worker_progress", text)
        self.assertIn("240.0", text)
        self.assertNotIn("TranscriptionWorker(", text)
        self.assertNotIn('EVENT_PREFIX = "AUDITOR_EVENT|"', text)

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

    def test_worker_has_no_stdout_ipc(self):
        text = (self.root / "app/file_worker_cli.py").read_text(encoding="utf-8")
        self.assertIn("class Progress", text)
        self.assertIn("progress_path", text)
        self.assertIn("FileTranscriptionService", text)
        self.assertNotIn("EVENT_PREFIX", text)
        self.assertNotIn("print(", text)


if __name__ == "__main__":
    unittest.main()
