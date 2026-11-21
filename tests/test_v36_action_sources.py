"""V36 source replacements are bounded to reviewed crop windows and never approve publishing."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_auto_v32 import add_v36_action_clips, RANK_FIVE_BOX, RANK_FIVE_BOX_SHA256
from v12_pexels_audition import official_video_id

def baseline():
    return [
      {"title":"File:Cat in a Bag.webm","editorial_quality_heuristic":57},
      {"title":"Pexels PX-40826295","editorial_quality_heuristic":59},
      {"title":"Pexels PX-34689563","editorial_quality_heuristic":63},
      {"title":"File:Katzensprung in Zeitlupe.webm","editorial_quality_heuristic":64},
      {"title":"File:Salto - Cat Jump.webm","editorial_quality_heuristic":95},
    ]

class V36EditorialTests(unittest.TestCase):
    def test_only_inspected_shots_replaced_and_rights_remain_blocked(self):
        self.assertEqual(official_video_id(RANK_FIVE_BOX),15135238)
        with TemporaryDirectory() as td, \
            patch("top5_auto_v32.source_digest",return_value=RANK_FIVE_BOX_SHA256), \
            patch("top5_auto_v32.download_single_pexels",
                  side_effect=[{"duration_sec":8.64},{"duration_sec":40.96}]):
            result,audit=add_v36_action_clips({"topic_id":"cat_surprises"},baseline(),td)
        self.assertEqual(len(result),5)
        self.assertEqual(result[0]["title"],"Pexels PX-15135238")
        self.assertAlmostEqual(result[0]["cut_start"],2.625)
        self.assertEqual(result[3]["title"],"File:Katzensprung in Zeitlupe.webm")
        self.assertFalse(result[0]["publication_approved"])
        self.assertEqual(audit["attempts"][-1]["reason_code"],
                         "V54_PAIR_SCENE_ACTION_NOT_VERIFIED")
        self.assertTrue(audit["attempts"][-1]["download_skipped"])
        self.assertFalse(audit["publication_approved"])
        self.assertFalse(audit["youtube_reused_content_approved"])
        self.assertTrue(audit["box_added"])
        self.assertFalse(audit["pair_added"])

    def test_unrelated_topic_not_modified(self):
        items=baseline()
        with TemporaryDirectory() as td:
            result,audit=add_v36_action_clips({"topic_id":"dog_surprises"},items,td)
        self.assertEqual(result,items)
        self.assertFalse(audit["publication_approved"])

    def test_missing_sources_are_not_fabricated(self):
        with TemporaryDirectory() as td, \
            patch("top5_auto_v32.download_single_pexels",side_effect=RuntimeError("blocked")):
            result,audit=add_v36_action_clips({"topic_id":"cat_surprises"},baseline(),td)
        self.assertEqual([x["title"] for x in result],
                         [x["title"] for x in baseline()])
        self.assertFalse(audit["box_added"])
        self.assertFalse(audit["pair_added"])
        self.assertFalse(audit["rights_independently_verified"])

    def test_changed_box_bytes_preserve_the_bag_source(self):
        with TemporaryDirectory() as td, \
            patch("top5_auto_v32.source_digest",return_value="wrong"), \
            patch("top5_auto_v32.download_single_pexels",
                  side_effect=[{"duration_sec":8.64},RuntimeError("blocked")]):
            result,audit=add_v36_action_clips({"topic_id":"cat_surprises"},baseline(),td)
        self.assertEqual(result[0]["title"],"File:Cat in a Bag.webm")
        self.assertFalse(audit["box_added"])

if __name__=="__main__": unittest.main()
