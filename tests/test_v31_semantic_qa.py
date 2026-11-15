"""V31 semantic advisory regression tests (no model download)."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v31_semantic_qa import prompts_for,sample_times,relative_verdict,summary,RANKS

class V31SemanticTests(unittest.TestCase):
    def test_v28_locked_rank_windows(self):
        self.assertEqual([x[0] for x in RANKS],[5,4,3,2,1])
        for _,a,b in RANKS:
            ts=sample_times(a,b)
            self.assertEqual(len(ts),8)
            self.assertGreater(ts[0],a)
            self.assertLess(ts[-1],b)
            self.assertEqual(ts,sorted(ts))
    def test_expected_and_alternatives(self):
        for name,label in [
            ("File:Cat in a Bag.webm","쇼핑백 점령"),
            ("File:Moomin1.webm","면봉 사냥"),
            ("File:Salto - Cat Jump.webm","건물 사이 점프"),
            ("File:Larry the cat and Chloé playing (100111224612).webm","둘의 눈치싸움")]:
            self.assertEqual(len(prompts_for(name,label)),4)
        self.assertIn("bag",prompts_for("File:Cat in a Bag.webm","쇼핑백 점령")[0])
    def test_non_calibrated_decisions(self):
        self.assertEqual(relative_verdict([.2,.6,.1,.1])["flag"],
                         "POSSIBLE_CAPTION_SCENE_MISMATCH")
        self.assertEqual(relative_verdict([.7,.1,.1,.1])["flag"],
                         "RELATIVE_TEXT_VIDEO_MATCH_ONLY")
        self.assertTrue(relative_verdict([.5,.3,.1,.1])["no_calibrated_confidence"])
    def test_rights_never_automatically_cleared(self):
        s=summary(["RELATIVE_TEXT_VIDEO_MATCH_ONLY"]*5)
        self.assertFalse(s["publication_approved"])
        self.assertFalse(s["copyright_and_licensing_cleared"])
        self.assertFalse(s["funny_outcome_certified"])

if __name__=="__main__":unittest.main()
