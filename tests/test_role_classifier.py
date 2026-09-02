import unittest
from app.services.role_classifier import infer_role_map
class RoleTests(unittest.TestCase):
    def test_client_can_speak_first(self):
        u=[{'speaker':'0','text':'Aló'},{'speaker':'1','text':'Buenas tardes mi nombre es Ana, le habla de Servipag'},{'speaker':'1','text':'En una escala del uno al siete ¿qué nota pondría?'},{'speaker':'0','text':'Seis'}]
        m=infer_role_map(u)
        self.assertEqual(m['1'],'AGENTE'); self.assertEqual(m['0'],'CLIENTE')
if __name__=='__main__': unittest.main()
