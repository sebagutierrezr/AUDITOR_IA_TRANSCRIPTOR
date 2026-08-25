from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Minimal stub: DiarizationService constructor references AppPaths only.
# We bypass __init__ in these pure logic tests.
from app.models.conversation import Conversation, Segment
from app.services.diarization_service import (
    AlignedWord,
    DiarizationService,
    RawUtterance,
    SpeakerTurn,
)


class SpeakerV2Tests(unittest.TestCase):
    def setUp(self):
        self.service = DiarizationService()

    def test_client_can_speak_first_but_agent_is_inferred(self):
        # Cliente dice "aló" primero. Luego el agente conduce la entrevista.
        utterances = [
            RawUtterance(
                "B",
                [
                    AlignedWord(0.0, 0.2, "Aló", "B"),
                ],
            ),
            RawUtterance(
                "A",
                [
                    AlignedWord(0.3, 0.5, " Hola", "A"),
                    AlignedWord(0.5, 0.8, ", mi nombre es", "A"),
                    AlignedWord(0.8, 1.1, " Ana.", "A"),
                    AlignedWord(1.1, 1.5, " ¿En una escala", "A"),
                    AlignedWord(1.5, 1.8, " del 1 al 7", "A"),
                    AlignedWord(1.8, 2.1, " qué nota", "A"),
                    AlignedWord(2.1, 2.3, " le pondría?", "A"),
                ],
            ),
            RawUtterance(
                "B",
                [
                    AlignedWord(2.4, 2.7, " Un seis.", "B"),
                ],
            ),
            RawUtterance(
                "A",
                [
                    AlignedWord(2.8, 3.2, " ¿Por qué motivo", "A"),
                    AlignedWord(3.2, 3.5, " nos evalúa así?", "A"),
                ],
            ),
        ]

        mapping = self.service._infer_speaker_map(
            raw_utterances=utterances,
            unique_speakers=["A", "B"],
            speaker_one_label="AGENTE",
            speaker_two_label="CLIENTE",
            first_speaker_is_one=True,
        )

        self.assertEqual(mapping["A"], "AGENTE")
        self.assertEqual(mapping["B"], "CLIENTE")

    def test_mixed_whisper_segment_splits_by_word(self):
        turns = [
            SpeakerTurn(0.0, 2.0, "A"),
            SpeakerTurn(2.0, 3.0, "B"),
        ]

        conversation = Conversation(
            source_path="x.wav",
            language="ES",
            segments=[
                Segment(
                    0.0,
                    3.0,
                    "¿QUÉ NOTA LE PONDRÍA? UN SEIS.",
                    words=[
                        {"start": 0.1, "end": 0.4, "text": " ¿QUÉ", "probability": .9},
                        {"start": 0.4, "end": 0.7, "text": " NOTA", "probability": .9},
                        {"start": 0.7, "end": 1.0, "text": " LE", "probability": .9},
                        {"start": 1.0, "end": 1.5, "text": " PONDRÍA?", "probability": .9},
                        {"start": 2.1, "end": 2.3, "text": " UN", "probability": .9},
                        {"start": 2.3, "end": 2.6, "text": " SEIS.", "probability": .9},
                    ],
                )
            ],
        )

        words = self.service._align_conversation_words(
            conversation,
            turns,
        )
        groups = self.service._group_words_into_utterances(
            words
        )

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].raw_speaker, "A")
        self.assertEqual(groups[1].raw_speaker, "B")
        self.assertIn("PONDRÍA", groups[0].text)
        self.assertIn("SEIS", groups[1].text)


    def test_progress_hook_reports_real_diarization_progress(self):
        events = []

        hook = self.service._make_progress_hook(
            lambda value, message: events.append(
                (value, message)
            )
        )

        hook(
            "segmentation",
            None,
            completed=1,
            total=4,
        )
        hook(
            "embeddings",
            None,
            completed=2,
            total=4,
        )
        hook(
            "discrete_diarization",
            None,
        )

        self.assertTrue(events)
        self.assertGreaterEqual(events[0][0], 92)
        self.assertLessEqual(events[-1][0], 98)
        self.assertTrue(
            any(
                "COMPARANDO IDENTIDAD" in message
                for _, message in events
            )
        )



if __name__ == "__main__":
    unittest.main()
