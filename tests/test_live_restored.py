from __future__ import annotations

import ast
import unittest
from pathlib import Path


class LiveStabilityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_live_modules_have_valid_python(self):
        for relative in (
            "app/ui/pages/live_page.py",
            "app/workers/unified_audio_worker.py",
            "app/workers/audio_test_worker.py",
            "app/services/audio_device_service.py",
        ):
            ast.parse((self.root / relative).read_text(encoding="utf-8"))

    def test_live_records_in_user_writable_appdata(self):
        text = (self.root / "app/ui/pages/live_page.py").read_text(encoding="utf-8")
        self.assertIn("recordings = self.paths.recordings", text)
        self.assertNotIn('self.paths.root / "recordings"', text)

    def test_client_capture_uses_wasapi_loopback(self):
        devices = (self.root / "app/services/audio_device_service.py").read_text(encoding="utf-8")
        worker = (self.root / "app/workers/unified_audio_worker.py").read_text(encoding="utf-8")
        self.assertIn("pyaudiowpatch", devices)
        self.assertIn("get_loopback_device_info_generator", devices)
        self.assertIn("get_default_wasapi_loopback", devices)
        self.assertIn("pyaudiowpatch", worker)
        self.assertIn("input_device_index=index", worker)

    def test_capture_and_transcription_are_separate_threads(self):
        text = (self.root / "app/workers/unified_audio_worker.py").read_text(encoding="utf-8")
        self.assertIn("_transcription_loop", text)
        self.assertIn("threading.Thread(target=self._transcription_loop", text)
        self.assertIn("self.jobs", text)
        self.assertIn("warmup", text)

    def test_live_decoder_is_low_latency(self):
        text = (self.root / "app/engines/faster_whisper_engine.py").read_text(encoding="utf-8")
        section = text[text.index("def transcribe_live"):]
        self.assertIn("beam_size=1", section)
        self.assertIn("best_of=1", section)


if __name__ == "__main__":
    unittest.main()
