"""V21 source diversity, no false jump descriptions, and 30s technical gate."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from v21_qa import validate_selection,EXPECTED_SLOTS,EXPECTED_SECONDS
from v12_mixed_draft import validate_mixed_selection

ROOT=Path(__file__).resolve().parents[1]

class V21QA(unittest.TestCase):
    def rows(self):
        return json.loads((ROOT/"sample/v21-mixed-selection.json").read_text(encoding="utf-8"))

    def test_five_distinct_originals_and_no_low_resolution(self):
        ids=validate_selection(self.rows())
        self.assertEqual(len(ids),5)
        self.assertEqual(len(set(ids)),5)
        self.assertFalse(any(x["audio_approved"] for x in self.rows()))

    def test_selection_exact_curated_pexels_pages(self):
        pages=json.loads((ROOT/"sample/v21-sources.json").read_text(encoding="utf-8"))
        validated=validate_mixed_selection(self.rows(),pages)
        self.assertEqual(len(validated),5)
        self.assertEqual(sum(x["provider"]=="pexels" for x in validated),3)

    def test_valid_rank_script_and_30s_timeline(self):
        script=json.loads((ROOT/"sample/v21-script.json").read_text(encoding="utf-8"))
        self.assertTrue(script["review_only"])
        self.assertFalse(script["publication_approved"])
        self.assertEqual(list(script["phases"]),["rank5","rank4","rank3","rank2","rank1"])
        self.assertTrue(all(len(x)==2 for x in script["phases"].values()))
        self.assertEqual(sum(EXPECTED_SECONDS),30)
        self.assertEqual(EXPECTED_SLOTS[1:6],["rank5","rank4","rank3","rank2","rank1"])

    def test_refuses_audio_rights_approval_and_duplicates(self):
        rows=self.rows()
        rows[0]["audio_approved"]=True
        with self.assertRaisesRegex(ValueError,"audio"):
            validate_selection(rows)
        rows=self.rows()
        rows[1]=dict(rows[0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate_selection(rows)

    def test_katzensprung_or_old_jump_cannot_reenter(self):
        rows=self.rows()
        rows[0]={"provider":"wikimedia","title":"File:Jump.webm",
                 "start_sec":1.0,"audio_approved":False,"display_name":"저화질"}
        with self.assertRaisesRegex(ValueError,"low-resolution"):
            validate_selection(rows)


if __name__=="__main__":
    unittest.main()
