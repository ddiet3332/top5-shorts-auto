"""V52: five distinct natural event types, not five different source filenames."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_candidate_visual_gate import diverse_scene_selection, nature_event_family
from top5_auto_v30 import select_sources
from top5_topic_recovery import source_shortage
from top5_hook_selection import SourceShortage

class NatureFiveDistinctFamiliesTest(unittest.TestCase):
    def test_actual_v51_montage_is_three_events_not_five(self):
        titles=[
            "File:Time Lapse - Aurora Borealis close to Berlin.webm",
            "File:Riverside geyser Yellowstone.ogv",
            "File:Time-lapse of Aurora Borealis in Norway.webm",
            "File:Strokkur geyser eruption in Iceland.webm",
            "File:Tonga Volcano Eruption satellite.webm",
        ]
        selected, rejected=diverse_scene_selection(
            [{"title":title} for title in titles],
            required=5,distinct_event_families_only=True)
        self.assertEqual(len(selected),3)
        self.assertEqual({nature_event_family(x["title"]) for x in selected},
                         {"aurora","geyser","volcano"})
        self.assertEqual(len(rejected),2)
        self.assertTrue(all(x["reason_code"]=="REPEATED_NATURE_EVENT_FAMILY"
                            for x in rejected))

    def test_unknown_nature_class_does_not_fake_fifth_event(self):
        titles=["File:Aurora Borealis.webm","File:Lightning at sea.webm",
                "File:Tonga Volcano.webm","File:Yellowstone geyser.webm",
                "File:Indistinct view 2026.webm"]
        selected, rejected=diverse_scene_selection(
            [{"title":title} for title in titles],
            required=5,distinct_event_families_only=True)
        self.assertEqual(len(selected),4)
        self.assertEqual(rejected[0]["reason_code"],"UNKNOWN_NATURE_EVENT_FAMILY")

    def test_source_selector_refuses_duplicate_nature_and_auto_can_fallback(self):
        titles=[
            "File:Time Lapse - Aurora Borealis close to Berlin.webm",
            "File:Riverside geyser Yellowstone.ogv",
            "File:Time-lapse of Aurora Borealis in Norway.webm",
            "File:Strokkur geyser eruption in Iceland.webm",
            "File:Tonga Volcano Eruption satellite.webm",
        ]
        candidates=[
            {"title":title, "source_page":f"https://commons.wikimedia.org/wiki/Source{i}",
             "author":f"creator{i}", "license":"CC BY 4.0",
             "license_url":"https://creativecommons.org/licenses/by/4.0/",
             "title_score":7.0} for i,title in enumerate(titles)]
        with tempfile.TemporaryDirectory() as folder:
            def download(src,path):
                Path(path).write_bytes(src["title"].encode())
            with (patch("top5_auto_v30.download_video",side_effect=download),
                  patch("top5_auto_v30.probe_duration",return_value=12.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(1.0,8.0)),
                  patch("top5_auto_v30.inspect_original_window",
                        return_value={"mostly_dark":False,"near_dark_count":0}),
                  patch("top5_auto_v30.checked_scenes",return_value={}),
                  patch("top5_auto_v30.reviewed_weak_window",return_value=None)):
                with self.assertRaises(SourceShortage) as err:
                    select_sources(candidates,Path(folder),topic={
                        "topic_id":"nature_moments","category":"자연"})
            self.assertIn("SOURCE_SHORTAGE_NATURE_EVENT_DIVERSITY",str(err.exception))
            self.assertTrue(source_shortage(str(err.exception)))
            audit=json.loads((Path(folder)/"V30_SOURCE_SCENE_DIVERSITY.json").read_text())
            self.assertEqual(audit["distinct_event_family_count"],3)
            self.assertEqual(len(set(audit["selected_event_families"])),3)
            self.assertTrue(audit["strict_one_nature_event_per_rank"])
            self.assertFalse(audit["publication_approved"])

    def test_five_distinct_events_still_selected(self):
        titles=["File:Aurora Borealis.webm","File:Lightning at sea.webm",
                "File:Tonga Volcano.webm","File:Yellowstone geyser.webm",
                "File:Alpine glacier.webm","File:Second geyser.webm"]
        selected,rejected=diverse_scene_selection(
            [{"title":title} for title in titles],required=5,
            distinct_event_families_only=True)
        self.assertEqual(len(selected),5)
        self.assertEqual(len({nature_event_family(x["title"]) for x in selected}),5)

if __name__=="__main__":
    unittest.main()
