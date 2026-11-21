"""Source/window-matched cached dog review must not falsely clear rights."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dog_preview_review import load_preview_rejections, is_evidenced_rejection
from dog_replacement_report import report


class PreviewReviewTests(unittest.TestCase):
    def setUp(self):
        self.reviews = load_preview_rejections(
            ROOT / "sample/dog_curated_preview_reviews_v1.json")

    def _sofa(self):
        return {"provider": "pexels", "id": "PX-33567553",
                "status": "PREVIEW_READY_REVIEW_REQUIRED",
                "sha256": "44e2e371c42446a68abd500bf38db7db80e8474fb1592bc8dd70150ddb436b05",
                "preview_start_sec": 28.0,
                "alternative_windows": [{"status": "PREVIEW_READY_REVIEW_REQUIRED",
                                          "preview_start_sec": 4.0}],
                "rights_status": "UNVERIFIED"}

    def _lake(self):
        return {"provider": "pexels", "id": "PX-28860202",
                "status": "PREVIEW_READY_REVIEW_REQUIRED",
                "sha256": "2b6097a5c19df33208b855fee985820bf01b0d214ee94cf415fcc15209b1ea81",
                "preview_start_sec": 2.0, "alternative_windows": [],
                "rights_status": "UNVERIFIED"}

    def test_only_exact_hash_and_all_reviewed_windows_are_rejected(self):
        self.assertTrue(is_evidenced_rejection(self._sofa(), self.reviews))
        self.assertTrue(is_evidenced_rejection(self._lake(), self.reviews))
        for mutation in ({"sha256": "0"*64},
                         {"preview_start_sec": 23.0},
                         {"alternative_windows": []},
                         {"alternative_windows": [
                             {"status": "PREVIEW_READY_REVIEW_REQUIRED", "preview_start_sec": 7.0}]}):
            with self.subTest(mutation=mutation):
                self.assertFalse(is_evidenced_rejection({**self._sofa(), **mutation}, self.reviews))
        self.assertFalse(is_evidenced_rejection({**self._lake(), "provider":"pixabay"},self.reviews))

    def test_review_manifest_cannot_claim_approval_or_rights(self):
        data=json.loads((ROOT/"sample/dog_curated_preview_reviews_v1.json").read_text())
        for field,value in (("publication_approved", True),
                            ("rights_status", "CLEARED"),
                            ("decision", "APPROVE"),
                            ("source_sha256", "x"*64)):
            modified=json.loads(json.dumps(data))
            if field=="publication_approved":
                modified[field]=value
            else:
                modified["rejections"][0][field]=value
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/"bad.json"
                path.write_text(json.dumps(modified))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    load_preview_rejections(path)

    def test_actual_rejected_cache_is_not_perpetually_pending_or_publishable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            profile={"shots":{"hook":{"source_id":"H","action":"bag"},
                "rank5":{"source_id":"A","action":"jump"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"B","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            p,a,feed=(root/"profile.json",root/"audition.json",root/"pexels.json")
            p.write_text(json.dumps(profile))
            a.write_text(json.dumps({"candidates":[]}))
            feed.write_text(json.dumps({"provider":"pexels","candidates":[self._sofa(),self._lake()]}))
            result=report(p,a,provider_reports=[feed],
                preview_review_path=ROOT/"sample/dog_curated_preview_reviews_v1.json")
            self.assertEqual(result["provider_preview_count"],0)
            self.assertEqual(result["provider_reviewed_rejected_count"],2)
            self.assertEqual(set(result["provider_reviewed_rejected_ids"]),
                             {"PX-33567553","PX-28860202"})
            self.assertEqual(result["next_action"],"DISCOVER_AND_REVIEW_CANDIDATES")
            self.assertFalse(result["publication_approved"])
            self.assertIsNone(result["editorial_score"])
            self.assertTrue(all(x["status"]=="PROVISIONAL_EDITORIAL_REJECTED"
                                and x["rights_status"]=="UNVERIFIED"
                                for x in result["provider_auditions"]))


if __name__ == "__main__":
    unittest.main()
