import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_artifact_resolver import expected_artifact


def items(*names):
    return {"artifacts": [{"name": n, "expired": False} for n in names]}


class ArtifactResolverTests(unittest.TestCase):
    def test_previous_dog_only_bug_fixed_for_generic_auto_and_selected_topic(self):
        self.assertEqual(expected_artifact(
            "TOP5 Topic-Driven Production", 62,
            items("TOP5-auto-review-62", "unrelated-preview")), "TOP5-auto-review-62")
        self.assertEqual(expected_artifact(
            "TOP5 Topic-Driven Production", 60,
            items("TOP5-dog_surprises-review-60")), "TOP5-dog_surprises-review-60")
        self.assertEqual(expected_artifact(
            "TOP5 Topic-Driven Production", 17,
            items("TOP5-nature_moments-review-17")), "TOP5-nature_moments-review-17")

    def test_original_v30_v32_regressions(self):
        self.assertEqual(expected_artifact(
            "TOP5 V32 - Auto stronger original 30s MP4", 92,
            items("TOP5-V32-auto-review-92")), "TOP5-V32-auto-review-92")
        self.assertEqual(expected_artifact(
            "TOP5 V30 - Auto discovery quality-gated MP4", 9,
            items("TOP5-V30-auto-review-9")), "TOP5-V30-auto-review-9")

    def test_never_selects_wrong_run_or_expired_artifact(self):
        with self.assertRaisesRegex(ValueError, "NO_UNIQUE"):
            expected_artifact("TOP5 Topic-Driven Production", 62,
                              items("TOP5-dog_surprises-review-61"))
        with self.assertRaisesRegex(ValueError, "NO_UNIQUE"):
            expected_artifact("TOP5 Topic-Driven Production", 62,
                              {"artifacts": [{"name": "TOP5-auto-review-62", "expired": True}]})
        with self.assertRaisesRegex(ValueError, "NO_UNIQUE"):
            expected_artifact("TOP5 Topic-Driven Production", 62,
                              items("TOP5-auto-review-62", "TOP5-dog_surprises-review-62"))

    def test_manual_explicit_name_and_unsupported_workflow(self):
        self.assertEqual(expected_artifact("MANUAL_EXPLICIT_ARTIFACT", 1,
                         items("TOP5-custom-review-123"), explicit="TOP5-custom-review-123"),
                         "TOP5-custom-review-123")
        with self.assertRaisesRegex(ValueError,"INVALID_EXPLICIT"):
            expected_artifact("MANUAL_EXPLICIT_ARTIFACT",1,items("../unsafe"),explicit="../unsafe")
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):
            expected_artifact("NOT_A_PRODUCTION_WORKFLOW",1,items("TOP5-auto-review-1"))


if __name__ == "__main__":
    unittest.main()
