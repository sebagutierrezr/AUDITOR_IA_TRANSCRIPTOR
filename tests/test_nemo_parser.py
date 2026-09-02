import unittest
from app.services.nemo_speech_service import NemoSpeechService
class NemoParserTests(unittest.TestCase):
    def test_collects_word_speaker_tags(self):
        d={'results':[{'alternatives':[{'words':[{'word':'hola','start_time':0.1,'end_time':0.3,'speaker_tag':1}]}]}]}
        w=NemoSpeechService._collect_words(d)
        self.assertEqual(w[0]['word'],'hola'); self.assertEqual(w[0]['speaker_tag'],1)
if __name__=='__main__': unittest.main()
