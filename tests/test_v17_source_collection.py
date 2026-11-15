"""Offline regression checks for the V17 source-diversity and review guardrails."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import v17_discovery as v17


class TestV17SourceCollection(unittest.TestCase):
    def test_every_search_and_category_gets_a_chance_before_cap(self):
        def fake_query(term, per_query):
            if term == "first":
                return [{"title": f"File:A{i}.webm"} for i in range(10)]
            return [{"title": "File:B0.webm"}, {"title": "File:A0.webm"},
                    {"title": "File:B1.webm"}]

        def fake_category(category, per_query):
            return [{"title": "File:C0.webm"}, {"title": "File:C1.webm"}]

        with patch.object(v17, "query_candidates", side_effect=fake_query), \
             patch.object(v17, "category_candidates", side_effect=fake_category):
            pool, search_log, failures = v17.collect_sources(
                searches=("first", "second"), categories=("category",), max_pool=6)

        titles = {item["title"] for item in pool}
        self.assertEqual(len(pool), 6)
        self.assertIn("File:A0.webm", titles)
        self.assertIn("File:B0.webm", titles)
        self.assertIn("File:C0.webm", titles)
        self.assertEqual(len(search_log), 3)
        self.assertEqual(failures, [])

    def test_source_failure_does_not_prevent_later_categories(self):
        with patch.object(v17, "query_candidates", side_effect=RuntimeError("api")), \
             patch.object(v17, "category_candidates", return_value=iter(
                 [{"title": "File:Safe.webm"}])):
            pool, queries, failures = v17.collect_sources(
                searches=("failed",), categories=("fallback",), max_pool=10)
        self.assertEqual([item["title"] for item in pool], ["File:Safe.webm"])
        self.assertEqual(len(failures), 1)
        self.assertEqual(queries[0]["term"], "fallback")

    def test_external_repost_is_not_automatically_approved(self):
        self.assertTrue(v17.is_external_reupload({
            "source_claim": "Reuploaded from https://youtube.com/example",
            "review_flags": []}))
        self.assertTrue(v17.is_external_reupload({
            "source_claim": "", "review_flags": ["외부 재게시 원본 권리 확인 필요"]}))
        self.assertFalse(v17.is_external_reupload({
            "source_claim": "own work", "review_flags": []}))

    def test_unrelated_search_hits_are_excluded(self):
        self.assertFalse(v17.likely_cat_candidate({
            "title": "File:Gurl skater.webm"}))
        self.assertFalse(v17.likely_cat_candidate({
            "title": "File:Perceptual-elements-in-magic-trick.ogv"}))
        self.assertFalse(v17.has_feline_title_evidence("File:Caterpillar.webm"))
        self.assertTrue(v17.likely_cat_candidate({
            "title": "File:Cat jumping backwards.webm"}))
        self.assertTrue(v17.likely_cat_candidate({
            "title": "File:Moomin1.webm", "cat_category_evidence": True}))
        self.assertFalse(v17.likely_cat_candidate({
            "title": "File:Moomin1.webm", "cat_category_evidence": False}))

    def test_cat_category_provenance_overrides_generic_title(self):
        def fake_query(term, per_query):
            return [{"title": "File:Unknown pet.webm"}]
        def fake_category(category, per_query):
            return [{"title": "File:Unknown pet.webm"}]
        with patch.object(v17, "query_candidates", side_effect=fake_query), \
             patch.object(v17, "category_candidates", side_effect=fake_category):
            pool, _, _ = v17.collect_sources(
                searches=("cat playing",), categories=("Videos of cats",),
                max_pool=10)
        self.assertEqual(len(pool), 1)
        self.assertTrue(pool[0]["cat_category_evidence"])
        self.assertTrue(v17.likely_cat_candidate(pool[0]))

    def test_reaction_stories_are_not_dropped_as_generic(self):
        self.assertEqual(
            v17.action_group("File:Cat discovers it was being spied on.webm"),
            "reaction")
        self.assertGreater(
            v17.editorial_priority({
                "title": "File:Cat discovers it was being spied on.webm",
                "source_claim": "Own work",
                "review_flags": []
            }),
            v17.editorial_priority({
                "title": "File:Cat at home.webm",
                "source_claim": "",
                "review_flags": []
            }))

    def test_media_budget_allows_larger_hd_cat_sources(self):
        defaults = v17.make_review.__defaults__
        self.assertEqual(defaults[2], 55*1024*1024)
        self.assertGreaterEqual(defaults[1], 180*1024*1024)

    def test_short_but_complete_cat_moments_remain_reviewable(self):
        self.assertEqual(v17.audition_seconds(4.333), 4.13)
        self.assertEqual(v17.audition_seconds(5.0), 4.8)
        self.assertEqual(v17.audition_seconds(5.5), 5.0)
        self.assertEqual(v17.audition_seconds(3.5), 0.0)
        self.assertEqual(v17.audition_seconds(241.0), 0.0)

    def test_minimum_source_quality(self):
        self.assertFalse(v17.sufficient_resolution(320, 240))
        self.assertTrue(v17.sufficient_resolution(720, 480))
        self.assertTrue(v17.sufficient_resolution(480, 720))
        self.assertFalse(v17.sufficient_resolution(640, 480))


if __name__ == "__main__":
    unittest.main()
