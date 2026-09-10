import unittest

from app.services.role_classifier import infer_role_map, refine_turn_roles


class RoleTests(unittest.TestCase):
    def test_client_can_speak_first(self):
        utterances = [
            {"speaker": "0", "text": "Aló"},
            {"speaker": "1", "text": "Buenas tardes mi nombre es Ana, le habla de Servipag"},
            {"speaker": "1", "text": "En una escala del uno al siete ¿qué nota pondría?"},
            {"speaker": "0", "text": "Seis"},
        ]
        mapping = infer_role_map(utterances)
        self.assertEqual(mapping["1"], "AGENTE")
        self.assertEqual(mapping["0"], "CLIENTE")

    def test_real_case_intro_wrong_cluster_is_corrected_locally(self):
        turns = [
            {
                "speaker": "0",
                "text": "Buen día me comunico con don Juan Andrés Correa Barrios",
                "start": 3.44,
                "end": 6.2,
                "words": [],
            },
            {
                "speaker": "1",
                "text": "Mi nombre es Loreto Riquelme pertenezco a la empresa Ipsos",
                "start": 7.0,
                "end": 12.0,
                "words": [],
            },
            {
                "speaker": "0",
                "text": "Tengo varios seguros de qué seguro están hablando",
                "start": 30.0,
                "end": 34.0,
                "words": [],
            },
            {
                "speaker": "1",
                "text": "Antes de continuar quisiera informarle que esta entrevista será grabada",
                "start": 50.0,
                "end": 58.0,
                "words": [],
            },
        ]
        mapping = infer_role_map(turns)
        refined = refine_turn_roles(turns, mapping)
        self.assertEqual(refined[0]["role"], "AGENTE")
        self.assertEqual(refined[2]["role"], "CLIENTE")

    def test_short_numeric_answer_stays_client(self):
        turns = [
            {"speaker": "A", "text": "Del cero al diez qué nota le pondría", "words": []},
            {"speaker": "A", "text": "Seis", "words": []},  # borde acústico pegado al agente
            {"speaker": "B", "text": "Porque encuentro que es caro", "words": []},
        ]
        role_map = {"A": "AGENTE", "B": "CLIENTE"}
        refined = refine_turn_roles(turns, role_map)
        self.assertEqual(refined[0]["role"], "AGENTE")
        self.assertEqual(refined[1]["role"], "CLIENTE")

    def test_mixed_client_confirmation_then_agent_intro_is_split(self):
        words = []
        tokens = ["Con", "él", "señorita", "mi", "nombre", "es", "Loreto"]
        t = 0.0
        for token in tokens:
            words.append({"text": token, "start": t, "end": t + 0.2})
            t += 0.22

        turns = [
            {
                "speaker": "A",
                "text": "Con él señorita mi nombre es Loreto",
                "start": 0.0,
                "end": t,
                "words": words,
            }
        ]
        role_map = {"A": "AGENTE"}
        refined = refine_turn_roles(turns, role_map)
        self.assertEqual(len(refined), 2)
        self.assertEqual(refined[0]["role"], "CLIENTE")
        self.assertEqual(refined[1]["role"], "AGENTE")
        self.assertIn("mi", refined[1]["text"].lower())


if __name__ == "__main__":
    unittest.main()
