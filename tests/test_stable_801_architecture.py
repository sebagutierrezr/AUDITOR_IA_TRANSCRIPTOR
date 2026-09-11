from __future__ import annotations

import ast
import unittest
from pathlib import Path


class Stable810ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_python_sources_compile(self):
        for path in (self.root / "app").rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        ast.parse((self.root / "main.py").read_text(encoding="utf-8"))

    def test_sortformer_does_not_use_unread_pipes(self):
        text = (self.root / "app/services/nemo_diarization_service.py").read_text(encoding="utf-8")
        self.assertIn('stdout=log_handle', text)
        self.assertIn('stderr=subprocess.STDOUT', text)
        self.assertNotIn('stdout=subprocess.PIPE', text)
        self.assertNotIn('stderr=subprocess.PIPE', text)

    def test_settings_contains_universal_diagnostics(self):
        text = (self.root / "app/ui/pages/settings_page.py").read_text(encoding="utf-8")
        self.assertIn("MODO DE RENDIMIENTO", text)
        self.assertIn("DIAGNÓSTICO DEL EQUIPO", text)
        self.assertIn("PYAUDIOWPATCH", text)
        diag = (self.root / "app/services/diagnostic_service.py").read_text(encoding="utf-8")
        self.assertIn("Faster-Whisper", diag)
        self.assertIn("SortFormer local", diag)

    def test_build_is_pinned_and_conversion_is_isolated(self):
        text = (self.root / ".github/workflows/build-release.yml").read_text(encoding="utf-8")
        self.assertIn("v0.1.0", text)
        self.assertIn(".convert-venv", text)
        self.assertIn("api.github.com/repos/NVIDIA/NeMo-Speech.cpp/releases/tags/v0.1.0", text)
        self.assertIn("AUDITOR_IA_8.1.0_Setup.exe", text)
        self.assertIn("pyaudiowpatch", text)

    def test_installer_upgrades_existing_80(self):
        text = (self.root / "installer/AUDITOR_IA.iss").read_text(encoding="utf-8")
        self.assertIn("AUDITORIA800", text)
        self.assertIn('MyAppVersion "8.1.0"', text)
        self.assertIn("WizardStyle=modern", text)


if __name__ == "__main__":
    unittest.main()
