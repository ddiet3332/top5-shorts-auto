import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from top5 import supported_license, clean_html, ass_timestamp, create_subtitles, DEFAULT_CAPTIONS, source_label, candidate_relevance, create_transition_sfx, voiceover_timeline, verify_editorial_selections

class BasicTests(unittest.TestCase):
    def test_license_positive(self):
        self.assertEqual(supported_license('https://creativecommons.org/licenses/by/4.0/'), 'CC BY')
        self.assertEqual(supported_license('http://creativecommons.org/licenses/by/3.0'), 'CC BY')
        self.assertEqual(supported_license('https://creativecommons.org/publicdomain/zero/1.0/'), 'CC0')
    def test_license_negative(self):
        for x in ('https://creativecommons.org/licenses/by-sa/4.0/',
                  'https://creativecommons.org/licenses/by-nc/4.0/',
                  'https://creativecommons.org/licenses/by-nd/4.0/',
                  'https://example.org/by/4.0', ''):
            self.assertIsNone(supported_license(x))
    def test_html(self):
        self.assertEqual(clean_html('<a href="/">Kim</a> &amp; Jane'), 'Kim & Jane')
    def test_source_names(self):
        self.assertEqual(source_label("File:Cat playing in Taiwan.webm", {"File:Cat playing in Taiwan.webm": "대만 고양이"}), "대만 고양이")
        self.assertTrue(source_label("File:Cat playing in Taiwan.webm").startswith("Cat playing"))

    def test_v3_relevance(self):
        self.assertEqual(candidate_relevance("Magician's Cat (2012).webm"), -100)
        self.assertGreater(candidate_relevance("Funny kitten jumping and playing.webm"), 0)
        self.assertEqual(candidate_relevance("Kenan Thompson playing every character on All That.webm"), -100)
        self.assertEqual(candidate_relevance("Fractal and DogPlayingTetris during CTWC.webm"), -100)
        self.assertEqual(candidate_relevance("This is what plays in my mind - Victorious.webm"), -100)
        self.assertGreaterEqual(candidate_relevance("Cat in a Bag.webm"), 0)

    def test_v3_audio_and_timeline(self):
        import tempfile
        import wave
        import json
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            create_transition_sfx(out/'effects.wav',seconds=30)
            with wave.open(str(out/'effects.wav')) as audio:
                self.assertEqual(audio.getframerate(),48000)
                self.assertEqual(audio.getnframes(),30*48000)
            lines=voiceover_timeline(out,DEFAULT_CAPTIONS)
            self.assertEqual(len(lines),7)
            self.assertEqual(lines[-1]['end'],30)
            self.assertTrue((out/'NARRATION_REQUIRED.md').exists())

    def test_editorial_selection_validation(self):
        rows=[{'title':f'File:Clip_{i:02}.webm','start_sec':3,'focus_x':0.5} for i in range(5)]
        self.assertEqual(len(verify_editorial_selections(rows)),5)
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4])
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4]+[rows[0]])
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4]+[{'title':'File:new.webm','focus_x':1.1}])

    def test_ass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.ass'
            create_subtitles(p,'재미있는 TOP5',DEFAULT_CAPTIONS)
            content=p.read_text(encoding='utf-8')
            self.assertEqual(content.count('Dialogue:'),1+1+7*11)
            self.assertIn('0:00:30.00',content)
            self.assertIn('ActiveName',content)
            self.assertIn('RankName',content)
if __name__=='__main__': unittest.main()
