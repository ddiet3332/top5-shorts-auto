"""V22 candidate QA preserves source diversity, rights and real-video review."""
import copy
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from v22_new_source_audition import checked_catalog,report_audition

CATALOG=Path(__file__).resolve().parents[1]/"sample/v22-new-candidates.json"


class V22NewCandidateTests(unittest.TestCase):
    def test_curated_pages_are_distinct_and_no_rights_approved(self):
        rows=checked_catalog(CATALOG)
        self.assertEqual(len(rows),3)
        self.assertEqual({r["action_group"] for r in rows},
                         {"box-in-out","toy-pounce","two-cats-play"})
        self.assertTrue(all(r["publication_approved"] is False for r in rows))
        self.assertTrue(all(r["source_audio_approved"] is False for r in rows))

    def test_rejected_old_weak_source_cannot_reenter(self):
        rows=json.loads(CATALOG.read_text(encoding="utf-8"))
        rows[0]["id"]="PX-17462877"
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"candidates.json"
            p.write_text(json.dumps(rows),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"low-payoff"):
                checked_catalog(p)

    def test_rejects_duplicate_action_group(self):
        rows=json.loads(CATALOG.read_text(encoding="utf-8"))
        rows[0]["action_group"]=rows[1]["action_group"]
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"candidates.json"
            p.write_text(json.dumps(rows),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"action categories"):
                checked_catalog(p)

    def test_no_preview_can_be_pretended_to_be_funny(self):
        rows=checked_catalog(CATALOG)
        with TemporaryDirectory() as tmp:
            report=report_audition(rows,[{
                "id":rows[0]["id"],
                "editorial_status":"VIDEO_READY_FOR_HUMAN_REVIEW",
                "windows":[{"source_time_sec":2.0,"preview_file":"preview_1.mp4"}]
            }],Path(tmp))
            self.assertEqual(report["preview_count"],1)
            self.assertEqual(report["previewable_originals"],1)
            self.assertIsNone(report["final_content_score"])
            self.assertFalse(report["publication_approved"])
            self.assertFalse(report["candidates"][0]["actual_video_watched"])
            self.assertFalse(report["candidates"][0]["windows"][0]["action_humor_verified"])

    def test_no_laundering_of_license_rights(self):
        rows=checked_catalog(CATALOG)
        with TemporaryDirectory() as tmp:
            report=report_audition(rows,[],Path(tmp))
            self.assertEqual(report["preview_count"],0)
            self.assertTrue(all(not x["source_license_independently_cleared"] for x in report["candidates"]))
            self.assertTrue(all(not x["explicit_third_party_rights_cleared"] for x in report["candidates"]))


if __name__=="__main__":
    unittest.main()
