"""Universal channel smoke QA must not turn dog-only or technical pass into YPP approval."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_universal_trial import TOPIC_FAMILIES, assess, catalog_check


def write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


class UniversalTrialTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.catalog = self.root / "sample/top5_auto_topics_v30.json"

    def test_all_four_families_have_real_catalog_topics(self):
        self.assertEqual(set(TOPIC_FAMILIES), {
            "cat_surprises", "human_moments", "nature_moments", "objects_oddities"})
        self.assertEqual({v[0] for v in TOPIC_FAMILIES.values()},
                         {"animals", "people", "nature", "objects"})
        for topic in TOPIC_FAMILIES:
            self.assertEqual(catalog_check(topic, self.catalog)["topic_id"], topic)
        with self.assertRaises(ValueError):
            catalog_check("dog_only_all_channel", self.catalog)

    def _evidence(self, out, topic):
        (out / "TOP5_AUTO_V29_REVIEW_1080x1920.mp4").write_bytes(b"test-render")
        write(out / "TOPIC_RECOMMENDATIONS_V32.json", {"chosen_topic": topic})
        write(out / "V32_TECHNICAL_QA.json", {
            "topic": topic, "full_decode": "PASS", "source_count": 5,
            "publication_approved": False,
            "source_permissions_fully_cleared": False})
        write(out / "SELECTED_SOURCE_PROVENANCE.json", {
            "selected": [{"sha256": hashlib.sha256(f"source {i}".encode()).hexdigest(),
                          "source_page": f"https://example.com/{i}",
                          "rights_verified": False,
                          "publication_approved": False} for i in range(5)],
            "rights_verified": False, "publication_approved": False})

    @staticmethod
    def _probe(_):
        return {"streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1080,
             "height": 1920, "r_frame_rate": "24/1", "nb_frames": "720"},
            {"codec_type": "audio", "codec_name": "aac"}],
            "format": {"duration": "30.000"}}

    def test_each_family_technical_pass_still_blocks_publication(self):
        for topic in TOPIC_FAMILIES:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)
                self._evidence(path, topic)
                result = assess(topic, path, probe=self._probe)
                self.assertEqual(result["status"], "TECHNICAL_PASS_REVIEW_ONLY")
                self.assertTrue(result["technical_pass"])
                self.assertIsNone(result["final_editorial_score_100"])
                self.assertFalse(result["publication_approved"])
                self.assertFalse(result["rights_verified"])

    def test_unmatched_topic_or_source_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self._evidence(p, "human_moments")
            self.assertEqual(assess("nature_moments", p, probe=self._probe)["status"],
                             "BLOCKED_INVALID_OUTPUT_EVIDENCE")
            src = json.loads((p / "SELECTED_SOURCE_PROVENANCE.json").read_text())
            src["selected"][3]["sha256"] = src["selected"][2]["sha256"]
            write(p / "SELECTED_SOURCE_PROVENANCE.json", src)
            self.assertFalse(assess("human_moments", p, probe=self._probe)["technical_pass"])
            self.assertFalse(assess("human_moments", p, probe=self._probe)["publication_approved"])

    def test_false_license_clearance_or_bad_mp4_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            self._evidence(p, "objects_oddities")
            q = json.loads((p / "V32_TECHNICAL_QA.json").read_text())
            q["publication_approved"] = True
            write(p / "V32_TECHNICAL_QA.json", q)
            self.assertFalse(assess("objects_oddities", p, probe=self._probe)["technical_pass"])
            q["publication_approved"] = False
            write(p / "V32_TECHNICAL_QA.json", q)
            def wrong_shape(_):
                z=self._probe(_)
                z["streams"][0]["nb_frames"]="250"
                return z
            self.assertFalse(assess("objects_oddities", p, probe=wrong_shape)["technical_pass"])

    def test_missing_mp4_does_not_claim_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            a=assess("cat_surprises",temp)
            self.assertEqual(a["status"],"BLOCKED_NO_VERIFIED_MP4")
            self.assertFalse(a["technical_pass"])
            self.assertFalse(a["publication_approved"])


if __name__ == "__main__":
    unittest.main()
