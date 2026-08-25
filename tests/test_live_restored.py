import ast
import unittest
from pathlib import Path


class LiveModuleStructureTests(unittest.TestCase):
    def test_live_files_exist(self):
        root = Path(__file__).resolve().parents[1]

        required = [
            root / "app/ui/pages/live_page.py",
            root / "app/services/audio_device_service.py",
            root / "app/workers/audio_test_worker.py",
            root / "app/workers/unified_audio_worker.py",
        ]

        for path in required:
            self.assertTrue(
                path.is_file(),
                str(path),
            )

    def test_live_modules_have_valid_python(self):
        root = Path(__file__).resolve().parents[1]

        for relative in [
            "app/ui/pages/live_page.py",
            "app/services/audio_device_service.py",
            "app/workers/audio_test_worker.py",
            "app/workers/unified_audio_worker.py",
        ]:
            path = root / relative
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )

    def test_main_window_has_live_navigation(self):
        root = Path(__file__).resolve().parents[1]
        text = (
            root
            / "app/ui/main_window.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            '("En vivo", self._live_page)',
            text,
        )


if __name__ == "__main__":
    unittest.main()
