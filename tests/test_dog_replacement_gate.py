"""Regression tests for editorial replacement safety gates."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_replacement_gate import evaluate_candidate, decide_replacements


def candidate(sid="PX-NEW", action="spin", score=90):
    return dict(id=sid, source_url="https://example.org/video", creator="Creator",
                license_url="https://example.org/license", sha256="a"*64,
                action_family=action, payoff_sec=2, start_sec=0,
                duration_sec=8, editorial_score=score, reviewed_frames=True,
                semantic_review="PASS", rights_status="CLEARED")


class ReplacementGateTests(unittest.TestCase):
    def test_valid_upgrade(self):
        d = evaluate_candidate("rank5", candidate(), used_ids=set(),
                               used_actions=set(), incumbent_score=60)
        self.assertEqual(d.status, "REPLACEMENT_ELIGIBLE")

    def test_missing_evidence_fails_closed(self):
        self.assertEqual(evaluate_candidate("rank5", {"id": "X"},
                         used_ids=set(), used_actions=set(), incumbent_score=60).status,
                         "NO_UPGRADE")

    def test_uncleared_rights_never_approved(self):
        c = candidate()
        c["rights_status"] = "UNVERIFIED"
        self.assertEqual(evaluate_candidate("rank2", c, used_ids=set(),
                         used_actions=set(), incumbent_score=60).reason,
                         "RIGHTS_REVIEW_REQUIRED")

    def test_no_semantic_review(self):
        c = candidate()
        c["semantic_review"] = "UNVERIFIED"
        self.assertEqual(evaluate_candidate("rank2", c, used_ids=set(),
                         used_actions=set(), incumbent_score=60).status, "NO_UPGRADE")

    def test_no_score_or_no_improvement(self):
        self.assertEqual(evaluate_candidate("rank5", candidate(score=50),
                         used_ids=set(), used_actions=set(), incumbent_score=60).status,
                         "NO_UPGRADE")
        self.assertEqual(evaluate_candidate("rank5", candidate(),
                         used_ids=set(), used_actions=set()).status, "NO_UPGRADE")

    def test_no_duplicate_action_across_ranks(self):
        result = decide_replacements(
            {"rank5": [candidate("A")], "rank2": [candidate("B")]},
            incumbent_scores={"rank5": 60, "rank2": 60},
            fixed_source_ids=set(), fixed_action_families=set())
        self.assertEqual([d.status for d in result],
                         ["REPLACEMENT_ELIGIBLE", "NO_UPGRADE"])

    def test_malformed_hash_rejected(self):
        c = candidate()
        c["sha256"] = "z" * 64
        self.assertEqual(evaluate_candidate("rank5", c, used_ids=set(),
                         used_actions=set(), incumbent_score=60).reason,
                         "MISSING_VERIFIED_HASH")

    def test_nan_score_rejected(self):
        c = candidate(score=float("nan"))
        self.assertEqual(evaluate_candidate("rank5", c, used_ids=set(),
                         used_actions=set(), incumbent_score=60).reason,
                         "NONFINITE_TIMING_OR_SCORE")

    def test_bad_candidate_score_does_not_crash_batch(self):
        c = candidate(score="not-a-number")
        decisions = decide_replacements({"rank5": [c]}, incumbent_scores={"rank5": 60},
                                        fixed_source_ids=set(), fixed_action_families=set())
        self.assertEqual(decisions[0].status, "NO_UPGRADE")

    def test_payoff_outside_window(self):
        c = candidate()
        c["payoff_sec"] = 5.5
        self.assertEqual(evaluate_candidate("rank5", c, used_ids=set(),
                         used_actions=set(), incumbent_score=60).status, "NO_UPGRADE")


if __name__ == "__main__":
    unittest.main()
