"""V28 high-contrast full-screen five-real-source commentary-only format."""
import sys,unittest
from tempfile import TemporaryDirectory
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v28_fullscreen_builder import (
    SEGMENTS,PAYOFFS,RANK_NAMES,FPS,W,H,build_ass
)
from v12_mixed_draft import validate_mixed_selection
import json

class V28NoClutterLayoutTests(unittest.TestCase):
    def test_fixed_five_unique_originals_30seconds(self):
        rows=json.loads((ROOT/"sample/v22-mixed-selection.json").read_text())
        catalog=json.loads((ROOT/"sample/v22-sources.json").read_text())
        self.assertEqual(len(validate_mixed_selection(rows,catalog)),5)
        self.assertFalse(any(row["audio_approved"] for row in rows))
        self.assertEqual(sum(x[1] for x in SEGMENTS),30)
        self.assertEqual([x[0] for x in SEGMENTS],
                         ["hook","rank5","rank4","rank3","rank2","rank1","outro"])
        self.assertEqual((W,H,FPS),(1080,1920,24))
    def test_one_short_editor_reaction_per_segment_and_no_story_cards(self):
        self.assertEqual(set(PAYOFFS),{x[0] for x in SEGMENTS})
        self.assertEqual(len(RANK_NAMES),5)
        self.assertTrue(all(isinstance(t[1],str) and len(t[1])<=21
                            for t in PAYOFFS.values()))
        self.assertEqual(PAYOFFS["rank5"][0],.42)
        self.assertEqual(PAYOFFS["rank4"][0],1.1)
        self.assertEqual(PAYOFFS["rank2"][0],2.5)
    def test_rendered_ass_safeguards(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"v28.ass"
            cues=build_ass(p)
            self.assertEqual(len([c for c in cues if ",Caption," in c]),6)
            self.assertEqual(len([c for c in cues if ",Outro," in c]),0)
            text=p.read_text()
            self.assertIn("0:00:02.00",text)
            self.assertNotIn("0:00:27.00,Outro",text)
            self.assertNotIn("고양이 돌발 행동 TOP5",text)
            self.assertEqual(len([c for c in cues if ",Upper," in c]),1)
            self.assertEqual(len([c for c in cues if ",SmallRank," in c]),1)
            self.assertTrue(any("0:00:00.00,0:00:27.00,Upper" in c for c in cues))
            self.assertTrue(any("0:00:00.00,0:00:27.00,SmallRank" in c for c in cues))
            self.assertIn("퇴장은 내일 하시나요?ㅋㅋ",text)
            self.assertIn("0:00:02.42",text)
            self.assertIn("0:00:07.10",text)
            self.assertIn("0:00:17.50",text)
            self.assertNotIn("EDITORIAL NOTE",text)
            self.assertNotIn("DRAFT / RIGHTS",text)
            self.assertNotIn("구독♥",text)
if __name__=="__main__":unittest.main()
