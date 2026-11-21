"""Ensure unattended replacement reporting never fabricates clearance or scores."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_replacement_report import report


class ReportTests(unittest.TestCase):
    def test_fresh_provider_previews_change_next_action_not_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            profile={"shots":{
                "hook":{"source_id":"A","action":"jump"},
                "rank5":{"source_id":"B","action":"leap"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"E","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            files = [root/"profile.json",root/"old.json",root/"pixabay.json",root/"commons.json"]
            payloads = [profile,{"candidates":[]},
                {"provider":"pixabay","candidates":[{
                    "id":"PB-123","status":"PREVIEW_READY_REVIEW_REQUIRED",
                    "rights_status":"UNVERIFIED","editorial_score":None}]},
                {"provider":"wikimedia_commons","candidates":[{
                    "id":"CM-abcdef123456","status":"AUDITION_FAILED"}]}]
            for file,payload in zip(files,payloads):
                file.write_text(json.dumps(payload),encoding="utf-8")
            result=report(files[0],files[1],provider_reports=files[2:])
            self.assertEqual(result["candidate_count"],0)
            self.assertEqual(result["provider_preview_count"],1)
            self.assertEqual(result["provider_preview_ids_pending_review"],["PB-123"])
            self.assertEqual(result["next_action"],"REVIEW_NEW_PREVIEWS")
            self.assertIsNone(result["editorial_score"])
            self.assertFalse(result["publication_approved"])
            self.assertTrue(all(d["status"]=="NO_UPGRADE" for d in result["decisions"]))

    def test_cached_review_queue_is_pending_not_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            profile={"shots":{
                "hook":{"source_id":"A","action":"jump"},
                "rank5":{"source_id":"B","action":"leap"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"E","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            p=root/"profile.json"
            p.write_text(json.dumps(profile))
            old=root/"old.json"
            old.write_text(json.dumps({"candidates":[]}))
            cached=root/"pixabay.json"
            cached.write_text(json.dumps({"provider":"pixabay","candidates":[
                {"id":"PB-111","status":"PREVIEW_READY_REVIEW_REQUIRED",
                 "preview_origin":"CACHED_PREVIOUS_RUN","publication_approved":False}]}))
            result=report(p,old,provider_reports=[cached])
            self.assertEqual(result["provider_preview_count"],1)
            self.assertEqual(result["provider_preview_new_count"],0)
            self.assertEqual(result["provider_preview_cached_count"],1)
            self.assertEqual(result["next_action"],"REVIEW_PENDING_PREVIEWS")
            self.assertFalse(result["publication_approved"])
            self.assertIsNone(result["editorial_score"])

    def test_unreviewed_candidates_do_not_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = {"shots": {
                "hook": {"source_id": "A", "action": "jump"},
                "rank5": {"source_id": "B", "action": "leap"},
                "rank4": {"source_id": "C", "action": "shake"},
                "rank3": {"source_id": "D", "action": "skate"},
                "rank2": {"source_id": "E", "action": "catch"},
                "rank1": {"source_id": "F", "action": "balance"},
                "outro": {"source_id": "F", "action": "tug"}}}
            audition = {"candidates": [{"id": "G", "rank_target": "rank5",
                                        "disposition": "PASSED_OVER"}]}
            p, a = root/"profile.json", root/"audition.json"
            p.write_text(json.dumps(profile))
            a.write_text(json.dumps(audition))
            result = report(p, a)
            self.assertEqual(result["candidate_count"], 1)
            self.assertTrue(all(d["status"] == "NO_UPGRADE" for d in result["decisions"]))
            self.assertIsNone(result["editorial_score"])
            self.assertFalse(result["publication_approved"])


if __name__ == "__main__":
    unittest.main()
