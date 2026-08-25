from __future__ import annotations

import unittest

from app.file_worker_cli import _conversation_to_dict
from app.models.conversation import Conversation, Segment


class FileWorkerProtocolTests(unittest.TestCase):
    def test_conversation_serializes(self):
        conversation = Conversation(
            source_path="audio.wav",
            language="ES",
            segments=[
                Segment(
                    start=0.0,
                    end=1.0,
                    text="AGENTE: HOLA",
                    speaker="AGENTE",
                    words=[{"start": 0.0, "end": 0.4, "text": "HOLA"}],
                )
            ],
        )
        result = _conversation_to_dict(conversation)
        self.assertEqual(result["language"], "ES")
        self.assertEqual(result["segments"][0]["speaker"], "AGENTE")
        self.assertEqual(result["segments"][0]["words"][0]["text"], "HOLA")


if __name__ == "__main__":
    unittest.main()
