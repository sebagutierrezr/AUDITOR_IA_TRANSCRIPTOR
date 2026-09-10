import unittest
import numpy as np

from app.models.conversation import Conversation, Segment
from app.services.diarization_service import DiarizationService, SpeakerTurn
from app.services.speaker_rescue_service import SpeakerRescueService


class SpeakerRescueTests(unittest.TestCase):
    def test_two_vectors_force_two_clusters(self):
        matrix = np.array(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float32,
        )
        labels = SpeakerRescueService._cluster_two(matrix)
        self.assertEqual(len(set(labels.tolist())), 2)

    def test_two_clear_voice_groups_cluster_without_sklearn(self):
        matrix = np.array(
            [
                [1.0, 0.02, 0.0],
                [0.98, 0.05, 0.0],
                [0.96, -0.03, 0.02],
                [0.02, 1.0, 0.0],
                [-0.04, 0.97, 0.01],
                [0.03, 0.95, -0.02],
            ],
            dtype=np.float32,
        )
        labels = SpeakerRescueService._cluster_two(matrix)
        self.assertEqual(len(set(labels.tolist())), 2)
        self.assertEqual(len(set(labels[:3].tolist())), 1)
        self.assertEqual(len(set(labels[3:].tolist())), 1)
        self.assertNotEqual(int(labels[0]), int(labels[3]))

    def test_cluster_two_has_no_sklearn_runtime_dependency(self):
        import inspect
        source = inspect.getsource(SpeakerRescueService._cluster_two)
        self.assertNotIn("sklearn", source)

    def test_candidate_chunks_keep_short_client_answer(self):
        conversation = Conversation(
            source_path="x.wav",
            language="ES",
            segments=[
                Segment(
                    0.0, 3.0, "PREGUNTA Y RESPUESTA",
                    words=[
                        {"start": 0.0, "end": 0.4, "text": " ¿QUÉ"},
                        {"start": 0.4, "end": 0.8, "text": " NOTA?"},
                        {"start": 1.4, "end": 1.6, "text": " SEIS."},
                    ],
                )
            ],
        )
        chunks = SpeakerRescueService._candidate_chunks(conversation)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(any((end - start) <= 0.5 for start, end in chunks))

    def test_suspicious_single_speaker_activates_rescue(self):
        turns = [SpeakerTurn(0.0, 20.0, "A")]
        self.assertTrue(DiarizationService._needs_rescue(turns, ["A"]))

    def test_balanced_two_speakers_do_not_force_rescue(self):
        turns = [
            SpeakerTurn(0.0, 5.0, "A"),
            SpeakerTurn(5.0, 8.0, "B"),
            SpeakerTurn(8.0, 12.0, "A"),
            SpeakerTurn(12.0, 16.0, "B"),
        ]
        self.assertFalse(DiarizationService._needs_rescue(turns, ["A", "B"]))


if __name__ == "__main__":
    unittest.main()
