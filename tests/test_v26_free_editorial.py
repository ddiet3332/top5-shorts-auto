"""V26 independent free-licence caption editorial gate regression."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v26_free_editorial_finish import validate_storyboard,make_ass

class V26FreeOriginalEditorial(unittest.TestCase):
    def data(self):
        return json.loads((ROOT/"sample/v26-free-editorial-storyboard.json").read_text(encoding="utf-8"))
    def test_no_narration_or_paid_stock(self):
        b=self.data()
        self.assertTrue(validate_storyboard(b))
        self.assertTrue(b["no_tts"])
        self.assertTrue(b["no_voiceover"])
        self.assertTrue(b["use_only_original_synthesized_sfx"])
        self.assertFalse(b["auto_publish"])
        self.assertEqual(b["duration_sec"],30)
        self.assertEqual(len(b["windows"]),12)
    def test_situation_payoffs_match_actual_frame_QA(self):
        b=self.data()
        beats={x["id"]:x for x in b["windows"]}
        self.assertAlmostEqual(beats["rank5_payoff"]["start_sec"],2.42)
        self.assertAlmostEqual(beats["rank4_payoff"]["start_sec"],7.1)
        self.assertAlmostEqual(beats["rank2_payoff"]["start_sec"],17.5)
        self.assertAlmostEqual(beats["rank1_payoff"]["start_sec"],23.2)
    def test_ASS_subtitle_contains_only_actual_ranked_story(self):
        b=self.data();text=make_ass(b)
        self.assertIn("반전 포착",text)
        self.assertIn("상자를 발견한 고양이",text)
        self.assertIn("한 번에 의자까지 올라섭니다",text)
        self.assertIn("도약의 크기",text)
        self.assertNotIn("RIGHTS REVIEW REQUIRED",text)
        self.assertNotIn("DRAFT",text)
        self.assertNotIn("TTS:",text)
        self.assertIn("저작자 표기: 영상 설명란",text)
    def test_rejects_missing_seconds_and_unapproved_audio(self):
        b=self.data();b["windows"][2]["start_sec"]=3.0
        with self.assertRaises(ValueError):validate_storyboard(b)
        b=self.data();b["no_voiceover"]=False
        with self.assertRaises(ValueError):validate_storyboard(b)
        b=self.data();b["auto_publish"]=True
        with self.assertRaises(ValueError):validate_storyboard(b)
        b=self.data();b["use_only_original_synthesized_sfx"]=False
        with self.assertRaises(ValueError):validate_storyboard(b)

if __name__=="__main__":
    unittest.main()
