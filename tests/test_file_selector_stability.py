from __future__ import annotations
import ast
import unittest
from pathlib import Path

class FileSelectorStabilityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.path = self.root / "app/ui/pages/files_page.py"
        self.text = self.path.read_text(encoding="utf-8")

    def test_no_native_static_dialog(self):
        self.assertNotIn("QFileDialog.getOpenFileName", self.text)

    def test_non_native_and_non_modal(self):
        self.assertIn("QFileDialog.Option.DontUseNativeDialog", self.text)
        self.assertIn("dialog.open()", self.text)
        self.assertNotIn("dialog.exec()", self.text)

    def test_starts_in_documents(self):
        self.assertIn("DocumentsLocation", self.text)

    def test_load_file_is_lightweight(self):
        tree = ast.parse(self.text)
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_load_file")
        source = ast.unparse(method)
        for forbidden in (".stat(", "av.open(", "torchaudio", "WhisperModel", "DiarizationService", "SpeakerRescueService"):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
