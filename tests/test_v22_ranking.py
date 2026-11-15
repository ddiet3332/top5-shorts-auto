"""V22 exact source replacements and original fixed 100-point controls."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v22_qa import validate_selection,EXPECTED_SLOTS,EXPECTED_SECONDS
from v12_mixed_draft import validate_mixed_selection

class TestV22Ranking(unittest.TestCase):
    def sources(self):
        return json.loads((ROOT/"sample/v22-mixed-selection.json").read_text(encoding="utf-8"))
    def test_rank5_rank4_replaced_from_actual_reviewed_windows(self):
        rows=self.sources()
        validate_selection(rows)
        self.assertEqual(rows[0]["id"],"PX-5495527")
        self.assertEqual(rows[0]["start_sec"],0)
        self.assertEqual(rows[1]["id"],"PX-9208508")
        self.assertEqual(rows[1]["start_sec"],24.0)
        self.assertNotIn("PX-17462877",str(rows))
        self.assertNotIn("PX-6187151",str(rows))
    def test_five_unique_actual_source_ids(self):
        rows=self.sources()
        catalog=json.loads((ROOT/"sample/v22-sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(validate_mixed_selection(rows,catalog)),5)
        self.assertEqual(len(set(validate_selection(rows))),5)
        self.assertEqual(sum(EXPECTED_SECONDS),30)
    def test_two_caption_phases_per_real_rank(self):
        script=json.loads((ROOT/"sample/v22-script.json").read_text(encoding="utf-8"))
        self.assertEqual(set(script["phases"]),
                         {"rank1","rank2","rank3","rank4","rank5"})
        self.assertTrue(all(len(p)==2 for p in script["phases"].values()))
        self.assertTrue(script["review_only"])
        self.assertFalse(script["publication_approved"])
    def test_source_audio_muted_and_publication_never_approved(self):
        rows=self.sources()
        self.assertTrue(all(r["audio_approved"] is False for r in rows))
        rows[0]["audio_approved"]=True
        with self.assertRaises(ValueError):
            validate_selection(rows)

if __name__=="__main__":
    unittest.main()
