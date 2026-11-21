"""Do not mistake five original objects for five distinct physical actions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_candidate_visual_gate import object_event_family,diverse_object_selection
from top5_auto_v30 import select_sources
from top5_hook_selection import SourceShortage


class ObjectEditorialDiversityTests(unittest.TestCase):
    def test_three_real_domino_ranks_against_two_other_mechanisms_are_blocked(self):
        labels=[
            "File:Domino Roach 2024.webm",
            'File:Efectul domino cu cărți la Biblioteca Centrală.webm',
            "File:Domino collapse at PAX 2009.ogv",
            "File:Arduino-blinkingLikeABouncingBall.ogv",
            "File:Bouncing Ball.webm",
        ]
        candidates=[{"title":x} for x in labels]
        selected,duplicate=diverse_object_selection(candidates)
        self.assertEqual(len(selected),4)
        self.assertEqual(sum(object_event_family(x["title"])=="domino" for x in selected),2)
        self.assertEqual(len(duplicate),1)
        self.assertEqual(duplicate[0]["reason_code"],"REPEATED_OBJECT_EVENT_FAMILY")

    def test_real_domino_roach_is_insect_not_physics_category(self):
        # V44 actual object rank 1 footage visibly shows an insect in leaf litter.
        # "Domino" in its name is a roach variety, NOT dominoes toppling.
        self.assertIsNone(object_event_family("File:Domino Roach 2024.webm"))
        self.assertIsNone(object_event_family("File:Beetle roach video.webm"))
        self.assertEqual(object_event_family("File:Robotic cockroach mechanism.webm"),"machine")
        chosen, rejected=diverse_object_selection([
            {"title":"File:Domino Roach 2024.webm"},
            {"title":"File:Domino Stop Motion.webm"},
            {"title":"File:Arduino circuit.webm"},
            {"title":"File:Bouncing Ball.webm"},
            {"title":"File:Newton's Cradle.webm"},
        ])
        self.assertEqual(len(chosen),4)
        self.assertEqual(rejected[0]["reason_code"],"UNKNOWN_OBJECT_EVENT_TYPE")
        self.assertNotIn("File:Domino Roach 2024.webm",[r["title"] for r in chosen])

    def test_five_distinct_physics_demonstrations_keep_separate_ranks(self):
        labels=[
            "File:Bouncing Ball.webm","File:Arduino circuit blinking.ogv",
            "File:Domino collapse.webm","File:Newton's cradle pendulum.webm",
            "File:Rube Goldberg machine.webm","File:Spinning top toy.webm"]
        sel,excluded=diverse_object_selection([{"title":x} for x in labels])
        self.assertEqual(len(sel),5)
        self.assertEqual(len({object_event_family(x["title"]) for x in sel}),5)
        self.assertIn(object_event_family("File:Arduino-blinkingLikeABouncingBall.ogv"),{"electronics"})
        self.assertEqual(object_event_family("File:Efectul domino cu cărți.webm"),"domino")
        self.assertEqual(object_event_family("File:Unclear1234.webm"),None)
        self.assertTrue(all(x["title"] not in ["File:Unclear1234.webm"] for x in sel))

    def test_actual_v30_candidate_loop_fails_closed_with_only_three_event_families(self):
        titles=["File:Domino step 1.webm","File:Domino step 2.webm",
                "File:Domino step 3.webm","File:Arduino circuit.webm",
                "File:Bouncing Ball.webm"]
        candidates=[{"title":t,"source_page":f"https://commons.wikimedia.org/wiki/{i}",
                     "author":f"maker-{i}","license":"CC BY",
                     "license_url":"https://creativecommons.org/licenses/by/4.0/",
                     "title_score":7.0,"discovery_rank":12.0}
                    for i,t in enumerate(titles)]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def fake_download(row,path):
                Path(path).write_bytes(row["title"].encode())
            with (patch("top5_auto_v30.download_video",side_effect=fake_download),
                  patch("top5_auto_v30.probe_duration",return_value=15.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(2.1,9.5)),
                  patch("top5_auto_v30.checked_scenes",return_value={}),
                  patch("top5_auto_v30.reviewed_weak_window",return_value=None)):
                with self.assertRaises(SourceShortage) as ctx:
                    select_sources(candidates,root,topic={
                        "topic_id":"objects_oddities","category":"사물"})
            self.assertIn("DISTINCT_OBJECT_EVENT_SHORTAGE",str(ctx.exception))
            doc=json.loads((root/"V30_SOURCE_SCENE_DIVERSITY.json").read_text())
            self.assertEqual(doc["selected_distinct_scene_count"],4)
            self.assertIsNone(doc["editorial_score"])
            self.assertFalse(doc["publication_approved"])


if __name__=="__main__":
    unittest.main()
