"""Topic-bound V31 semantic QA is advisory, never a fake creative or rights pass."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v31_semantic_qa import prompts_for,verified_topic_context,repair_worklist

class TopicAwareSemanticTests(unittest.TestCase):
    def test_anonymous_cat_pexels_stock_is_screened_as_cat(self):
        prompts=prompts_for("Pexels PX-15135238","","cat_surprises")
        self.assertEqual(len(prompts),4)
        self.assertIn("cat",prompts[0].lower())
        self.assertIn("without cats",prompts[3].lower())

    def test_nature_event_specific_prompts_avoid_generic_cat_or_volcano(self):
        cases=[
            ("File:1938 Atwood flood.webm","floodwater"),
            ("File:Strokkur geyser eruption.webm","geyser"),
            ("File:Aurora borealis Berlin.webm","aurora"),
            ("File:Tornado near Kansas.webm","tornado"),
            ("File:Snow avalanche on Alps.webm","avalanche"),
            ("File:Ocean waves crashing.mp4","waves"),
            ("File:Glacier calving.webm","glacier"),
            ("File:Hail storm.webm","hailstones"),
            ("File:Tonga Volcano Eruption.webm","volcano"),
            ("File:Kawaida Waterfall cascading.webm","waterfall"),
        ]
        for title,keyword in cases:
            with self.subTest(title=title):
                prompts=prompts_for(title,"장면 검수 필요","nature_moments")
                self.assertEqual(len(prompts),4)
                self.assertIn(keyword,prompts[0].lower())
                self.assertNotIn("cat playing",prompts[0].lower())

    def test_person_and_object_topic_unknowns_are_not_misclassified_as_cats(self):
        prompts=prompts_for("Pixabay 77004","","human_moments")
        self.assertIn("person",prompts[0])
        self.assertIn("silhouettes",prompts[1])
        self.assertIsNone(prompts_for("File:Unrecognized Machine.webm","","objects_oddities"))
        self.assertIsNone(prompts_for("File:Unrecognized.mp4","","nature_moments"))
        with self.assertRaisesRegex(ValueError,"UNVERIFIED"):
            prompts_for("Anything","","future_unknown_genre")

    def test_topic_must_come_from_actual_render_choice_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"TOPIC_RECOMMENDATIONS.json"
            self.assertIsNone(verified_topic_context(None))
            p.write_text(json.dumps({"chosen_topic":"cat_surprises"}))
            self.assertEqual(verified_topic_context(p),"cat_surprises")
            p.write_text(json.dumps({"chosen_topic":"not_a_real_topic"}))
            with self.assertRaisesRegex(ValueError,"UNVERIFIED"):
                verified_topic_context(p)

    def test_rank_one_mismatch_is_first_replacement_target_not_publishable(self):
        def row(rank,flag,motion):
            return {"rank":rank,"original_title":f"rank{rank}",
                    "verdict":{"flag":flag},
                    "motion_proxy":{"fraction_low_change":motion}}
        ranked=[
            row(5,"RELATIVE_TEXT_VIDEO_MATCH_ONLY",0.2),
            row(4,"UNSUPPORTED_SUBJECT_NEEDS_EDITORIAL_REVIEW",0.1),
            row(3,"POSSIBLE_CAPTION_SCENE_MISMATCH",0.3),
            row(2,"RELATIVE_TEXT_VIDEO_MATCH_ONLY",0.8),
            row(1,"POSSIBLE_CAPTION_SCENE_MISMATCH",0.5)]
        work=repair_worklist(ranked,"nature_moments")
        self.assertEqual([x["rank"] for x in work],[1,3,4,2,5])
        self.assertTrue(all(x["suggested_creative_caption"] is None for x in work))
        self.assertTrue(all(not x["caption_ready_to_render"] for x in work))
        self.assertTrue(all(not x["ranking_payoff_verified"] for x in work))
        self.assertTrue(all(not x["publisher_rights_verified"] for x in work))
        self.assertIn("CHECK_ACTION",work[3]["next_action"])


if __name__=="__main__":
    unittest.main()
