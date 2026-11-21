"""Auto TOP5 must test a variety of source-viable subjects, not default to cats."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_auto_v30 import choose_topic


TOPICS=[
    {"topic_id":"cat_surprises","headline":"cat","category":"동물"},
    {"topic_id":"nature_moments","headline":"nature","category":"자연"},
    {"topic_id":"objects_oddities","headline":"objects","category":"사물"},
    {"topic_id":"human_moments","headline":"humans","category":"사람"},
]

def fake_discovery(topic,discover=True):
    number=1 if topic["topic_id"]=="human_moments" else 5
    return [{"title":f"{topic['topic_id']}_{i}","discovery_rank":50.0 if topic["topic_id"]=="cat_surprises" else 6.0}
            for i in range(number)],[]


class MultiCategoryRotationTests(unittest.TestCase):
    def test_auto_rotates_only_among_viable_topic_families(self):
        seen=set()
        with patch("top5_auto_v30.discover_for_topic",side_effect=fake_discovery):
            for seed in range(6):
                with patch.dict(os.environ,{"TOP5_ROTATION_SEED":str(seed)}):
                    topic,rows,standings=choose_topic(TOPICS,"auto")
                    seen.add(topic["category"])
                    self.assertEqual(len(rows),5)
                    self.assertEqual(len(standings),4)
                    self.assertNotEqual(topic["topic_id"],"human_moments")
            self.assertEqual(seen,{"동물","사물","자연"})

    def test_same_seed_selects_same_topic_and_manual_override_still_works(self):
        with patch("top5_auto_v30.discover_for_topic",side_effect=fake_discovery):
            with patch.dict(os.environ,{"TOP5_ROTATION_SEED":"7"}):
                t1=choose_topic(TOPICS,"auto")[0]["topic_id"]
                t2=choose_topic(TOPICS,"auto")[0]["topic_id"]
                self.assertEqual(t1,t2)
                self.assertEqual(choose_topic(TOPICS,"human_moments")[0]["topic_id"],
                                 "human_moments")

    def test_bad_seed_is_rejected_and_unseeded_mode_preserved(self):
        with patch("top5_auto_v30.discover_for_topic",side_effect=fake_discovery):
            with patch.dict(os.environ,{"TOP5_ROTATION_SEED":"7.1"}):
                with self.assertRaises(ValueError):
                    choose_topic(TOPICS,"auto")
            with patch.dict(os.environ,{"TOP5_ROTATION_SEED":"0"}):
                self.assertNotEqual(choose_topic(TOPICS,"auto")[0]["topic_id"],
                                    "human_moments")


if __name__=="__main__":
    unittest.main()
