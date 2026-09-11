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
            "app/services/audio_capture_backend.py",
        ):
            ast.parse((self.root / relative).read_text(encoding="utf-8"))

    def test_live_records_in_user_writable_appdata(self):
        text = (self.root / "app/ui/pages/live_page.py").read_text(encoding="utf-8")
        self.assertIn("recordings = self.paths.recordings", text)
        self.assertNotIn('self.paths.root / "recordings"', text)

    def test_client_capture_has_wasapi_primary_and_soundcard_fallback(self):
        devices = (self.root / "app/services/audio_device_service.py").read_text(encoding="utf-8")
        backend = (self.root / "app/services/audio_capture_backend.py").read_text(encoding="utf-8")
        worker = (self.root / "app/workers/unified_audio_worker.py").read_text(encoding="utf-8")
        req = (self.root / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("PyAudioWPatch==0.2.12.8", req)
        self.assertIn("SoundCard==0.4.6", req)
        self.assertIn("get_loopback_device_info_generator", devices)
        self.assertIn("PyAudioWPatchLoopback", backend)
        self.assertIn("SoundCardLoopback", backend)
        self.assertIn("LoopbackCaptureFactory.create", worker)

    def test_transcription_uses_single_bounded_worker_lifecycle(self):
        text = (self.root / "app/workers/unified_audio_worker.py").read_text(encoding="utf-8")
        self.assertNotIn("_transcription_loop", text)
        self.assertNotIn("transcriber_thread", text)
        self.assertIn("self.transcribe(job)", text)
        self.assertIn("maxsize=self.system_profile.tuning.live_queue_limit", text)
        self.assertIn("queue.Full", text)

    def test_live_decoder_is_adaptive_and_rejects_silence(self):
        text = (self.root / "app/engines/faster_whisper_engine.py").read_text(encoding="utf-8")
        section = text[text.index("def transcribe_live"):]
        self.assertIn("self._system_profile.tuning.live_beam_size", section)
        self.assertIn("vad_filter=True", section)
        self.assertIn("no_speech_prob >= 0.58", section)
        self.assertIn("avg_logprob < -0.92", section)

    def test_live_vad_calibrates_noise_and_has_stable_thresholds(self):
        text = (self.root / "app/workers/unified_audio_worker.py").read_text(encoding="utf-8")
        self.assertIn("_calibration_frames", text)
        self.assertIn("silence_ms: int = 920", text)
        self.assertIn("base_rms=0.00018 * factor", text)
        self.assertIn("base_rms=0.00040 * factor", text)
        self.assertIn("snr_db < 5.0", text)

    def test_live_rejects_repeated_whisper_loops(self):
        text = (self.root / "app/services/live_text_guard.py").read_text(encoding="utf-8")
        self.assertIn("unique_ratio <= 0.30", text)
        self.assertIn("suscríbete", text)
        self.assertIn("suscribirte", text)

    def test_editor_allows_manual_scroll_while_transcribing(self):
        text = (self.root / "app/ui/pages/live_page.py").read_text(encoding="utf-8")
        self.assertIn('QPushButton("AUTO-SEGUIR: SÍ")', text)
        self.assertIn("pause_live_follow_for_review", text)
        self.assertIn("QEvent.Type.Wheel", text)
        self.assertIn("sliderPressed.connect", text)
        self.assertIn("QTextCursor(self.editor.document())", text)
        self.assertIn("scrollbar.setValue(previous_scroll)", text)
        self.assertIn("ScrollBarAlwaysOn", text)


if __name__ == "__main__":
    unittest.main()
