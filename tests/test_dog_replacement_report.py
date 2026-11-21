"""Ensure unattended replacement reporting never fabricates clearance or scores."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_replacement_report import report


class ReportTests(unittest.TestCase):
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
