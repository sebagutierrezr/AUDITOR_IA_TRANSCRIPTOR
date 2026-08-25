from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.patch_speechbrain_windows import (
    NEW_EXPRESSION,
    patch_file,
)


class SpeechBrainWindowsPatchTests(unittest.TestCase):
    def test_replaces_posix_only_inspect_check(self):
        source = '''
import os
if (
    importer_frame is not None
    and importer_frame.filename.endswith(
        "/inspect.py"
    )
):
    raise AttributeError()
'''.lstrip()

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "importutils.py"
            path.write_text(source, encoding="utf-8")

            changed = patch_file(path)
            result = path.read_text(encoding="utf-8")

            self.assertTrue(changed)
            self.assertIn(NEW_EXPRESSION, result)
            self.assertNotIn("filename.endswith", result)

    def test_patch_is_idempotent(self):
        source = (
            "import os\n"
            "if os.path.basename(importer_frame.filename) == "
            "\"inspect.py\":\n"
            "    raise AttributeError()\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "importutils.py"
            path.write_text(source, encoding="utf-8")

            changed = patch_file(path)
            self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
