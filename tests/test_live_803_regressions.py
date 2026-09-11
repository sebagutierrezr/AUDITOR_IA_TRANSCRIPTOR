from __future__ import annotations

import unittest

from app.services.live_text_guard import LiveTextGuard, TranscriptCandidate


class Live803RegressionTests(unittest.TestCase):
    def test_pc_audio_duplicate_is_not_agent(self):
        agent = TranscriptCandidate(
            "AGENTE",
            "NO TE PREOCUPES YA ESTA AHI QUE TE PASA SIENTO ESE IGUAL",
            32.0,
            40.0,
        )
        client = TranscriptCandidate(
            "CLIENTE",
            "NO TE PREOCUPES NO TE PREOCUPES YA ESTA AHI QUE TE PASA",
            31.0,
            39.0,
        )
        self.assertTrue(LiveTextGuard.same_source_audio(agent, client))

    def test_real_simultaneous_different_speech_is_kept(self):
        agent = TranscriptCandidate(
            "AGENTE",
            "BUENAS TARDES MI NOMBRE ES CAROLINA Y LLAMO DE IPSOS",
            10.0,
            15.0,
        )
        client = TranscriptCandidate(
            "CLIENTE",
            "SI DIGAME TENGO UNOS MINUTOS PARA RESPONDER",
            11.0,
            15.5,
        )
        self.assertFalse(LiveTextGuard.same_source_audio(agent, client))

    def test_suscribete_hallucination_is_rejected(self):
        self.assertTrue(LiveTextGuard.hallucination("¡SUSCRÍBETE!"))
        self.assertTrue(LiveTextGuard.hallucination("No olvides suscribirte"))

    def test_normal_short_answer_is_not_rejected(self):
        self.assertFalse(LiveTextGuard.hallucination("Sí, tengo tiempo"))


if __name__ == "__main__":
    unittest.main()
