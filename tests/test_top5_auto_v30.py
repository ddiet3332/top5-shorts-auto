"""V30: locked layout, broad topics and never-PUBLISH guard."""
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_auto_v30 import discover_for_topic,write_gates,checked_scenes,apply_curated_cut_shift
from v28_fullscreen_builder import ASS_HEAD,SEGMENTS,W,H,FPS

class V30QA(unittest.TestCase):
    def test_locked_visual_spec(self):
        self.assertIn("Style: Caption,NanumSquare,60,",ASS_HEAD)
        self.assertIn("Style: MainTopic,NanumSquare,59,",ASS_HEAD)
        self.assertEqual((W,H,FPS),(1080,1920,24))
        self.assertEqual(sum(sec for _,sec in SEGMENTS),30)

    def test_nonanimal_topics_still_supported(self):
        topics=json.loads((ROOT/"sample/top5_auto_topics_v30.json").read_text())
        self.assertEqual(set(x["category"] for x in topics),
                         {"동물","자연","사물","사람"})
        self.assertIn("File:Moomin1.webm",
                      next(t for t in topics if t["topic_id"]=="cat_surprises")["seeds"])

    def test_low_rated_prior_scene_is_blocked(self):
        checked=checked_scenes()
        self.assertLess(checked["File:Cat chasing a pigeon.webm"]["story_strength"],55)
        topic=next(t for t in json.loads(
            (ROOT/"sample/top5_auto_topics_v30.json").read_text())
            if t["topic_id"]=="cat_surprises")
        def row(title):
            return {"title":title,"size_bytes":1000000,"source_claim":"Own work",
                    "author":"Original creator","license":"CC0",
                    "license_url":"https://creativecommons.org/publicdomain/zero/1.0",
                    "source_page":"https://commons.wikimedia.org/wiki/"+title.replace(" ","_")}
        with patch("top5_auto_v30.find_seed_candidates",
                   return_value=[row("File:Cat chasing a pigeon.webm"),
                                 row("File:Salto - Cat Jump.webm"),
                                 row("File:Moomin1.webm")]):
            candidates,errors=discover_for_topic(topic,discover=False)
        selected=[x["title"] for x in candidates]
        self.assertNotIn("File:Cat chasing a pigeon.webm",selected)
        self.assertIn("File:Salto - Cat Jump.webm",selected)
        self.assertIn("File:Moomin1.webm",selected)

    def test_curated_cut_only_moves_reviewed_source_and_clamps(self):
        shifted=apply_curated_cut_shift("File:Katzensprung in Zeitlupe.webm",9.0,23.9)
        self.assertAlmostEqual(shifted,9.0,places=1)  # Reverted after V31 A/B showed empty tail
        untouched=apply_curated_cut_shift("File:Unreviewed Source.webm",3.1,25.0)
        self.assertEqual(untouched,3.1)

    def test_rights_never_autocleared(self):
        with TemporaryDirectory() as td:
            items=[{"title":f"File:Cat {i}.webm",
                    "caption":"눈여겨보세요","editorial_quality_heuristic":50,
                    "review_basis":"metadata_only"} for i in range(5)]
            q=write_gates(Path(td),{"topic_id":"cat_surprises"},items,[],[])
            self.assertFalse(q["publication_approved"])
            self.assertIsNone(q["quality_target_75_met"])
            self.assertFalse(q["copyright_and_ypp_verified"])
            self.assertEqual(len(q["rank_5_to_1"]),5)

if __name__=="__main__":
    unittest.main()
