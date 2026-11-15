"""V18 editorial handoff refuses to mistake metadata for video review."""
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from v18_editorial_handoff import review_template, validate_handoff, write_handoff


def fixture():
    items = []
    for i in range(1, 7):
        items.append({
            "title": f"File:Cat {i}.webm",
            "source_page": f"https://commons.wikimedia.org/wiki/File:Cat_{i}.webm",
            "license_metadata": "CC BY 4.0",
            "author_metadata": f"Author {i}",
            "width": 1920, "height": 1080, "duration_sec": 18.0,
            "review_moments": [{"start_sec": 2.0, "preview_duration_sec": 5.0}],
            "action_group_filename_hint": "leap" if i % 2 else "play",
            "publication_approved": False,
        })
    index = {"run_id": 43667599999, "run_number": 59,
             "review_status": "READY_FOR_MANUAL_QA", "candidates": items}
    decisions = review_template(index)
    decisions["hook_caption"] = "이 장면 중 가장 놀라운 반전은 무엇일까요?"
    decisions["outro_caption"] = "여러분의 최고의 장면은 몇 위인가요?"
    for rank, row in zip((5, 4, 3, 2, 1), decisions["candidates"][:5]):
        row.update({
            "editorial_selected_rank": rank,
            "reviewed_real_preview": True,
            "visible_behavior": "고양이가 실제로 몸을 움직여 장난감 쪽으로 이동하는 장면",
            "why_funny_or_surprising": "장난감이 옆으로 움직이는 순간 고양이가 반대 방향을 쳐다보는 반전",
            "rank_display_name": f"기습 고양이 {rank}",
            "caption_setup": "장난감을 쫓아가는 줄 알았는데",
            "caption_payoff": "갑자기 반대편을 보는 고양이!",
            "chosen_start_sec": 2.0,
        })
    return index, decisions


class V18EditorialHandoffTests(unittest.TestCase):
    def test_blank_template_never_approves(self):
        index, _ = fixture()
        t = review_template(index)
        self.assertEqual(len(t["candidates"]), 6)
        self.assertFalse(t["candidates"][0]["reviewed_real_preview"])
        self.assertIsNone(t["candidates"][0]["editorial_selected_rank"])
        self.assertFalse(t["publication_approved"])

    def test_valid_five_produce_selections_and_phases_not_rights(self):
        index, decisions = fixture()
        choices, script, evidence = validate_handoff(index, decisions)
        self.assertEqual(len(choices), 5)
        self.assertEqual([x["title"] for x in choices],
                         [f"File:Cat {i}.webm" for i in range(1, 6)])
        self.assertEqual(len(script["phases"]), 5)
        self.assertFalse(evidence["license_review_complete"])
        self.assertTrue(all(x["audio_approved"] is False for x in choices))
        with TemporaryDirectory() as td:
            write_handoff(index, decisions, Path(td))
            self.assertTrue((Path(td) / "V18_EDITORIAL_SELECTION.json").exists())

    def test_four_selected_do_not_pass(self):
        index, decisions = fixture()
        decisions["candidates"][4]["editorial_selected_rank"] = None
        with self.assertRaisesRegex(ValueError, "Five unique"):
            validate_handoff(index, decisions)

    def test_no_mismatched_run(self):
        index, decisions = fixture()
        decisions["source_run_id"] = 111
        with self.assertRaisesRegex(ValueError, "source run"):
            validate_handoff(index, decisions)

    def test_no_unverified_clip(self):
        index, decisions = fixture()
        decisions["candidates"][0]["reviewed_real_preview"] = False
        with self.assertRaisesRegex(ValueError, "Not actually reviewed"):
            validate_handoff(index, decisions)

    def test_no_unseen_start_window(self):
        index, decisions = fixture()
        decisions["candidates"][0]["chosen_start_sec"] = 8.0
        with self.assertRaisesRegex(ValueError, "actually generated"):
            validate_handoff(index, decisions)

    def test_no_four_second_source_in_five_second_rank(self):
        index, decisions = fixture()
        index["candidates"][0]["duration_sec"] = 4.33
        with self.assertRaisesRegex(ValueError, "retiming"):
            validate_handoff(index, decisions)

    def test_no_false_publication_approval(self):
        index, decisions = fixture()
        decisions["publication_approved"] = True
        with self.assertRaisesRegex(ValueError, "publication"):
            validate_handoff(index, decisions)

    def test_duplicate_source_rejected(self):
        index, decisions = fixture()
        decisions["candidates"][1]["title"] = decisions["candidates"][0]["title"]
        with self.assertRaises(ValueError):
            validate_handoff(index, decisions)

    def test_script_requires_actual_observation(self):
        index, decisions = fixture()
        decisions["candidates"][0]["visible_behavior"] = ""
        with self.assertRaisesRegex(ValueError, "visible_behavior"):
            validate_handoff(index, decisions)


if __name__ == "__main__":
    unittest.main()
