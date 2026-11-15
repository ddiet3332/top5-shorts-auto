"""Do not regress the TOP5 content QA rubric or pretend raw clips are finished."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qa_scorecard import RUBRIC, TOTAL, template, assess, markdown


class TestQAScorecard(unittest.TestCase):
    def test_original_weights_are_unchanged(self):
        self.assertEqual([n for _, _, n in RUBRIC], [20, 25, 15, 15, 10, 10, 5])
        self.assertEqual(TOTAL, 100)

    def test_candidate_audition_is_unscored(self):
        t = template("run-59")
        self.assertIsNone(t["total_score"])
        self.assertTrue(all(v is None for v in t["scores"].values()))
        self.assertFalse(t["publication_approved"])
        self.assertIn("미평가", markdown(t))

    def test_77_point_edit_still_requires_improvement(self):
        scores = {key: 0 for key, _, _ in RUBRIC}
        scores.update({"hook_first_2s": 17,
                       "humor_payoff": 19,
                       "ranking_convincing": 12,
                       "pacing_transitions": 12,
                       "creative_captions": 7,
                       "sound_immersion": 7,
                       "rights_monetization_readiness": 3})
        r = assess(scores, edited_video_reviewed=True, rights_cleared=False)
        self.assertEqual(r["total_score"], 77)
        self.assertEqual(r["content_grade"], "IMPROVE")
        self.assertFalse(r["publication_approved"])

    def test_100_still_does_not_override_rights(self):
        scores = {key: maximum for key, _, maximum in RUBRIC}
        r = assess(scores, edited_video_reviewed=True, rights_cleared=False)
        self.assertEqual(r["total_score"], 100)
        self.assertEqual(r["content_grade"], "PUBLISH_CANDIDATE")
        self.assertFalse(r["publication_approved"])

    def test_no_invented_score_on_raw_source(self):
        scores = {key: maximum for key, _, maximum in RUBRIC}
        with self.assertRaises(ValueError):
            assess(scores, edited_video_reviewed=False)
        with self.assertRaises(ValueError):
            assess({"hook_first_2s": 20}, edited_video_reviewed=True)


if __name__ == "__main__":
    unittest.main()
