"""V56: river flooding is not just a 'flood' filename token.

Real V55 #44927994610 scanned 32/44 Commons nature candidates, accepted
16 real video cuts but strict classifier counted 4 event types. Its distinct
Garonne River Overflow candidate is a fifth type *for metadata routing
only*. Actual visual payoff and rights require independent checks.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_candidate_visual_gate import nature_event_family, diverse_scene_selection


class RiverOverflowNatureRoutingTests(unittest.TestCase):
    def test_actual_garonne_original_is_flood_event_metadata_only(self):
        self.assertEqual(nature_event_family(
            "File:2022-01-11 Garonne River Overflow 5472.webm"),"flood")
        self.assertEqual(nature_event_family(
            "File:Russian River Overflow 2023.webm"),"flood")
        self.assertEqual(nature_event_family(
            "File:Small Stream Overflowing.webm"),"flood")

    def test_an_unrelated_software_overflow_does_not_become_flood(self):
        self.assertIsNone(nature_event_family(
            "File:Stack buffer overflow in neural network animation.webm"))
        self.assertIsNone(nature_event_family(
            "File:Ocean water overflow design.webm"))
        self.assertIsNone(nature_event_family(
            "File:Overflow toy mechanism.webm"))
        self.assertEqual(nature_event_family(
            "File:2020 flood in Atwood.webm"),"flood")

    def test_original_4_events_plus_garonne_become_five_unique_families(self):
        sources=[
            "File:Tonga Volcano Eruption 2022-01-15 visible.webm",
            "File:White Dome Geyser erupting.webm",
            "File:Aurora borealis from Slovenia.webm",
            "File:Video from behind Kawaida Waterfall.webm",
            "File:2022-01-11 Garonne River Overflow 5472.webm",
            "File:Strokkur geyser eruption in Iceland.webm",
        ]
        chosen,duplicates=diverse_scene_selection(
            [{"title":s} for s in sources],required=5,
            distinct_event_families_only=True)
        self.assertEqual(len(chosen),5)
        self.assertEqual({nature_event_family(x["title"]) for x in chosen},
                         {"volcano","geyser","aurora","waterfall","flood"})
        self.assertEqual(len(duplicates),1)
        self.assertEqual(duplicates[0]["reason_code"],
                         "REPEATED_NATURE_EVENT_FAMILY")

if __name__=="__main__":
    unittest.main()
