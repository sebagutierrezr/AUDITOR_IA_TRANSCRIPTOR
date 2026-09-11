from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

from app.services.audio_device_service import AudioDeviceService, InputDevice, OutputDevice
from app.services.live_text_guard import LiveTextGuard, TranscriptCandidate
from app.services.system_profile_service import SystemProfileService


class Universal810Tests(unittest.TestCase):
    def test_device_selection_prefers_saved_uid_then_default(self):
        inputs = [
            InputDevice(1, "A", "A", 48000, is_default=False, uid="sd:1:a"),
            InputDevice(2, "B", "B", 48000, is_default=True, uid="sd:2:b"),
        ]
        self.assertEqual(AudioDeviceService.select_input(inputs).uid, "sd:2:b")
        self.assertEqual(AudioDeviceService.select_input(inputs, "sd:1:a").uid, "sd:1:a")

        outputs = [
            OutputDevice("pawp:1", "A", "A", False, backend="PYAUDIOWPATCH"),
            OutputDevice("pawp:2", "B", "B", True, backend="PYAUDIOWPATCH"),
        ]
        self.assertEqual(AudioDeviceService.select_output(outputs).id, "pawp:2")
        self.assertEqual(AudioDeviceService.select_output(outputs, "pawp:1").id, "pawp:1")

    def test_performance_modes_have_bounded_threads(self):
        for mode in ("ECO", "BALANCEADO", "CALIDAD"):
            profile = SystemProfileService.detect(mode)
            self.assertGreaterEqual(profile.tuning.cpu_threads, 1)
            self.assertLessEqual(profile.tuning.cpu_threads, profile.logical_cores)
            self.assertGreater(profile.tuning.live_queue_limit, 0)

    def test_acoustic_signature_detects_same_pc_audio_with_different_text(self):
        rate = 16000
        t = np.arange(rate * 2, dtype=np.float32) / rate
        source = 0.25 * np.sin(2 * np.pi * 220 * t) + 0.08 * np.sin(2 * np.pi * 440 * t)
        leaked = source * 0.38
        a = TranscriptCandidate(
            "AGENTE", "texto bastante distinto por error del ASR", 10.0, 12.0,
            LiveTextGuard.audio_signature(leaked, rate),
        )
        c = TranscriptCandidate(
            "CLIENTE", "la frase correcta que viene del computador", 10.1, 12.1,
            LiveTextGuard.audio_signature(source, rate),
        )
        self.assertTrue(LiveTextGuard.same_source_audio(a, c))

    def test_acoustic_signature_keeps_simultaneous_different_sources(self):
        rate = 16000
        t = np.arange(rate * 2, dtype=np.float32) / rate
        agent_audio = np.sin(2 * np.pi * 190 * t).astype(np.float32)
        client_audio = np.sin(2 * np.pi * 680 * t).astype(np.float32)
        a = TranscriptCandidate(
            "AGENTE", "buenas tardes mi nombre es maria", 10.0, 12.0,
            LiveTextGuard.audio_signature(agent_audio, rate),
        )
        c = TranscriptCandidate(
            "CLIENTE", "si digame en que le puedo ayudar", 10.0, 12.0,
            LiveTextGuard.audio_signature(client_audio, rate),
        )
        self.assertFalse(LiveTextGuard.same_source_audio(a, c))

    def test_loopback_auto_prefers_pyaudio_backend(self):
        pawp = [OutputDevice("pawp:4", "Headset", "Headset", True, backend="PYAUDIOWPATCH", backend_index=4)]
        sc = [OutputDevice("soundcard:x", "Headset", "Headset", True, backend="SOUNDCARD")]
        with patch.object(AudioDeviceService, "_list_pawp_outputs", return_value=pawp), \
             patch.object(AudioDeviceService, "_list_soundcard_outputs", return_value=sc):
            result = AudioDeviceService.list_outputs("AUTO")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].backend, "PYAUDIOWPATCH")


if __name__ == "__main__":
    unittest.main()
