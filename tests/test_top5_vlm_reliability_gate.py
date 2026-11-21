"""Reject actual 256M video-description failure modes before subtitle drafting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_vlm_reliability_gate import (
    repeated_clause_ratio,reliability_rejections,evaluate_generated_report)

class ModelTextFailClosedTests(unittest.TestCase):
    def test_real_pig_scaffold_repetition_is_rejected(self):
        pig="The pig is being lifted up by a metal rod. "*11
        self.assertGreater(repeated_clause_ratio(pig),.22)
        flags=reliability_rejections(pig,"File:Kinetic sculpture.webm",
                                    {"adjacent_gray_change":[33.,34.]})
        self.assertIn("DEGENERATE_REPEATED_PHRASES",flags)
    def test_actual_purdue_hallucinated_korean_hello_is_blocked(self):
        text=('The first video shows a person in a workshop with a large machine. '
              'The text in the second video says "안녕하세요" (Hello, hello).')
        flags=reliability_rejections(text,
            "File:2019 Purdue National Chain Reaction Competition Winner.webm",
            {"adjacent_gray_change":[40.,53.]})
        self.assertIn("UNVERIFIED_TEXT_OR_OCR_CLAIM",flags)
        self.assertIn("GENERATED_KOREAN_WORDS_NOT_PROVEN_BY_VISUAL_QA",flags)
        self.assertIn("CHRONOLOGICAL_FRAMES_CONFUSED_FOR_SEPARATE_VIDEOS",flags)
    def test_book_domino_ignored_and_ball_movement_marked_uncertain(self):
        text="The woman in the center is walking down the hallway."
        flags=reliability_rejections(text,"File:Efectul domino cu cărți.webm",
                                    {"adjacent_gray_change":[44.,39.]})
        self.assertIn("FILENAME_EVENT_NOT_DESCRIBED_RECHECK",flags)
        ball="The first frame shows a red ball. The action is unclear or nearly static."
        flags=reliability_rejections(ball,"File:The Rube Goldberg Idea Machine.webm",
                                    {"adjacent_gray_change":[24.,49.]})
        self.assertIn("MODEL_STATIC_CLAIM_CONFLICTS_WITH_FRAME_CHANGES",flags)
    def test_v41_real_500m_static_inventory_never_becomes_action_caption(self):
        real={
          5:("File:Arduino-blinkingLikeABouncingBall.ogv",
              "The first frame shows a person working on a computer, the second shows a person working on a computer."),
          4:("File:Elefanterna kinetic sculpture.webm",
              "The first frame shows a window with a pink pig hanging from it. The second frame shows a pink pig hanging from a metal pole."),
          3:("File:The Rube Goldberg Idea Machine.webm",
              "The first frame shows a green object on a yellow surface, the second frame shows a red ball on a green object, and the third frame shows a purple funnel on a yellow surface."),
          1:("File:2019 Purdue National Chain Reaction Competition Winner.webm",
              "The first frame shows a person working on a machine. The second frame shows a person sitting on the floor."),
        }
        for rank,(title,description) in real.items():
            with self.subTest(rank=rank):
                flags=reliability_rejections(description,title,
                    {"adjacent_gray_change":[12.,24.]})
                self.assertIn("NO_CLEAR_TEMPORAL_ACTION_DESCRIBED_RECHECK",flags)

    def test_overlay_text_in_korean_not_mistaken_for_source_action(self):
        text="The first frame shows stars, while the second has text in Korean."
        flags=reliability_rejections(text,"File:Aurora lights.webm",
                                     {"adjacent_gray_change":[6.,7.]})
        self.assertIn("UNVERIFIED_TEXT_OR_OCR_CLAIM",flags)
        text2="A satellite image appears, followed by a text overlay with Korean text."
        flags2=reliability_rejections(text2,"File:Lightning satellite.webm",
                                      {"adjacent_gray_change":[5.,9.]})
        self.assertIn("UNVERIFIED_TEXT_OR_OCR_CLAIM",flags2)

    def test_no_flags_still_cannot_certify_visual_truth(self):
        description="A small orange ball moves through a visible series of tracks."
        self.assertEqual(reliability_rejections(description,"File:Sample.webm",
                         {"adjacent_gray_change":[5.,8.]}),[])
    def test_actual_report_must_stay_unverified_and_sha_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data={
                "chosen_topic":"objects_oddities",
                "model":"HuggingFaceTB/SmolVLM2-256M-Video-Instruct",
                "rendered_video_sha256":"b"*64,
                "publication_approved":False,
                "score_100":None,
                "korean_caption_ready":False,
                "rows":[{
                    "rank":4,
                    "source_sha256":"a"*64,
                    "generated_visual_description_en":"The pig is being lifted up by a metal rod. "*10,
                    "source_title_for_human_review":"File:Kinetic sculpture.webm",
                    "relative_frame_change":{"adjacent_gray_change":[33.,34.]},
                    "publication_approved":False,"real_action_verified":False,
                }]
            }
            path=root/"model.json";path.write_text(json.dumps(data))
            result=evaluate_generated_report(path)
            self.assertEqual(result["ranks_with_explicit_model_red_flags"],1)
            self.assertIsNone(result["score_100"])
            self.assertFalse(result["publication_approved"])
            self.assertFalse(result["rows"][0]["eligible_for_direct_korean_caption"])
            data["rows"][0]["publication_approved"]=True
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"SHA_INVALID"):
                evaluate_generated_report(path)

if __name__=="__main__":
    unittest.main()
