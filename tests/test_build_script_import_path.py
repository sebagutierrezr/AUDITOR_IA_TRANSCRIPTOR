from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BuildScriptImportPathTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def _check_script_can_import_app(self, relative_script: str):
        script = self.root / relative_script

        probe = f"""
import runpy
import sys
from pathlib import Path

script = Path(r"{script}")

# Reproducir el contexto de un script ejecutado fuera de la raíz:
sys.path = [str(script.parent)] + [
    item for item in sys.path
    if item not in ("", str(script.parent), r"{self.root}")
]

namespace = runpy.run_path(
    str(script),
    run_name="auditor_build_probe",
)

project_root = str(
    namespace["PROJECT_ROOT"]
)

assert project_root in sys.path, (
    "La raíz del proyecto no fue agregada a sys.path"
)

from app.services.speechbrain_compat import (
    patch_speechbrain_lazy_import,
)

print("APP_IMPORT_OK")
"""

        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)

            result = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=temp,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout,
        )
        self.assertIn(
            "APP_IMPORT_OK",
            result.stdout,
        )

    def test_verify_native_runtime_can_import_app(self):
        self._check_script_can_import_app(
            "scripts/verify_native_runtime.py"
        )

    def test_verify_ecapa_can_import_app(self):
        self._check_script_can_import_app(
            "scripts/verify_speaker_rescue_model.py"
        )


if __name__ == "__main__":
    unittest.main()
