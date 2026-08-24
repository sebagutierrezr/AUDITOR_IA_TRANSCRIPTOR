from __future__ import annotations

import unittest

from app.services.high_precision_transcription_service import HighPrecisionTranscriptionService
from app.services.openai_key_service import OpenAIKeyService


class FakeSegment:
    def __init__(self, speaker, start, end, text):
        self.speaker = speaker
        self.start = start
        self.end = end
        self.text = text


class FakeResponse:
    def __init__(self, segments):
        self.segments = segments


class HighPrecisionTests(unittest.TestCase):
    def setUp(self):
        self.service = HighPrecisionTranscriptionService()

    def test_extracts_two_speakers(self):
        response = FakeResponse(
            [
                FakeSegment("A", 0.0, 1.0, "Aló"),
                FakeSegment("B", 1.1, 3.5, "Hola, mi nombre es Ana"),
            ]
        )
        rows = self.service._extract_segments(response)
        self.assertEqual(set(self.service._speakers(rows)), {"A", "B"})

    def test_agent_can_be_second_speaker(self):
        rows = [
            {"speaker": "CLIENT_VOICE", "start": 0.0, "end": 0.5, "text": "Aló."},
            {
                "speaker": "AGENT_VOICE",
                "start": 0.6,
                "end": 4.0,
                "text": "Buenas tardes, mi nombre es Ana y le habla por una encuesta.",
            },
            {
                "speaker": "AGENT_VOICE",
                "start": 4.1,
                "end": 7.0,
                "text": "En una escala de uno a siete, ¿qué nota le pondría al servicio?",
            },
            {"speaker": "CLIENT_VOICE", "start": 7.1, "end": 7.8, "text": "Un seis."},
            {
                "speaker": "AGENT_VOICE",
                "start": 7.9,
                "end": 10.0,
                "text": "¿Por qué motivo nos evalúa con un seis?",
            },
        ]
        mapping, confidence, reason = self.service._heuristic_roles(
            rows,
            ["AGENT_VOICE", "CLIENT_VOICE"],
            "AGENTE",
            "CLIENTE",
        )
        self.assertEqual(mapping["AGENT_VOICE"], "AGENTE")
        self.assertEqual(mapping["CLIENT_VOICE"], "CLIENTE")
        self.assertGreaterEqual(confidence, 0.55)
        self.assertTrue(reason)

    def test_merges_adjacent_same_role(self):
        rows = [
            {"speaker": "A", "start": 0.0, "end": 1.0, "text": "Hola"},
            {"speaker": "A", "start": 1.1, "end": 2.0, "text": "buenas tardes"},
            {"speaker": "B", "start": 2.2, "end": 3.0, "text": "Hola"},
        ]
        output = self.service._build_segments(
            rows,
            {"A": "AGENTE", "B": "CLIENTE"},
            uppercase=True,
            show_timestamps=False,
        )
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0].speaker, "AGENTE")
        self.assertIn("HOLA BUENAS TARDES", output[0].text)
        self.assertEqual(output[1].speaker, "CLIENTE")

    def test_key_mask_hides_key(self):
        key = "sk-proj-1234567890abcdefghijkl"
        masked = OpenAIKeyService.masked(key)
        self.assertNotEqual(masked, key)
        self.assertTrue(masked.startswith("sk-"))
        self.assertTrue(masked.endswith("ijkl"))


if __name__ == "__main__":
    unittest.main()
