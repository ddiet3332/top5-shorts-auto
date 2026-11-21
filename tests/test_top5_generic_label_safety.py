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

    def test_real_source_selection_receives_topic_and_cannot_raise_name_error(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from top5_auto_v30 import select_sources
        from pathlib import Path

        candidates=[
            {"title": f"File:Waterfall View {i}.webm",
             "source_page": f"https://commons.wikimedia.org/wiki/File:Waterfall_View_{i}.webm",
             "author": f"creator-{i}", "license": "CC BY",
             "license_url": "https://creativecommons.org/licenses/by/4.0/",
             "title_score": 9.0, "discovery_rank": 15.0}
            for i in range(5)]
        def fake_download(row, path):
            Path(path).write_bytes((row["title"]+" content").encode())
        with TemporaryDirectory() as td:
            with (patch("top5_auto_v30.download_video",side_effect=fake_download),
                  patch("top5_auto_v30.probe_duration",return_value=11.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(1.0,11.0)),
                  patch("top5_auto_v30.checked_scenes",return_value={})):
                selected,attempts=select_sources(candidates,Path(td),
                    topic={"category":"자연","topic_id":"nature_moments"})
            self.assertEqual(len(selected),5)
            self.assertEqual(len(attempts),5)
            self.assertTrue(all(row["caption"]=="장면 내용 검수 필요" for row in selected))
            self.assertTrue(all(row["label"]=="폭포 관련 영상" for row in selected))

    def test_unfamiliar_human_topic_does_not_become_dog(self):
        self.assertEqual(provisional_topic_label({"category":"사람"},"File:Unknown.mp4"),
                         "사람 장면 검수 필요")


if __name__ == "__main__":
    unittest.main()
