"""Generic visual QA text must not falsely describe nonanimal events."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_auto_v30 import provisional_topic_label


class GenericLabelSafetyTests(unittest.TestCase):
    def test_waterfall_does_not_become_failed_accident(self):
        topic={"category":"자연"}
        self.assertEqual(provisional_topic_label(
            topic,"File:Side view video of Kawaida Waterfall cascading.webm"),
            "폭포 관련 영상")
        self.assertNotIn("실수", provisional_topic_label(topic,"Waterfall"))

    def test_lightning_storm_does_not_become_rotation(self):
        self.assertEqual(provisional_topic_label(
            {"category":"자연"},"File:Lightning Storm in Rolla.webm"),
            "번개 관련 영상")
        self.assertNotIn("회전", provisional_topic_label(
            {"category":"자연"},"File:Lightning Storm in Rolla.webm"))

    def test_arbitrary_domino_and_arduino_titles_do_not_claim_observed_action(self):
        self.assertEqual(provisional_topic_label({"category":"사물"},
                         "File:Domino Stop Motion.webm"),"도미노 관련 영상")
        self.assertEqual(provisional_topic_label({"category":"사물"},
                         "File:Arduino-blinkingLikeABouncingBall.ogv"),
                         "전자장치 시연")

    def test_unfamiliar_human_topic_does_not_become_dog(self):
        self.assertEqual(provisional_topic_label({"category":"사람"},"File:Unknown.mp4"),
                         "사람 장면 검수 필요")


if __name__ == "__main__":
    unittest.main()
