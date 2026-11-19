import hashlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import top5_production_review as review
from top5_free_topic_planner import trend_matches
from top5_free_source_download import acquire, obvious_topic_mismatch
from top5_watchdog_artifacts import inspect_artifact


class ProductionReviewTests(unittest.TestCase):
    def test_verified_score_requires_rights_for_candidate(self):
        with TemporaryDirectory() as folder:
            video = Path(folder) / "result.mp4"
            video.write_bytes(b"mock video")
            sha = hashlib.sha256(video.read_bytes()).hexdigest()
            report = {"sha256": sha, "scorecard": {key: {} for key in review.CATEGORIES}}
            qa = {"editorial_scores": review.CATEGORIES,
                  "full_video_review_evidence": {"video_sha256": sha, "reviewed": True,
                                                 "reviewer": "검수 담당", "reviewed_at": "2026-11-20"}}
            review.apply_independent_review(report, video, [], qa, {})
            self.assertEqual(report["editorial_score"], 100)
            self.assertEqual(report["status"], "RIGHTS_UNVERIFIED")

    def test_initial_black_cut_uses_later_clean_cut(self):
        with patch.object(review, "media_check", side_effect=["black_start:0", ""]) as check:
            self.assertEqual(review.select_start(Path("clip.mp4"), 10), 2)
            self.assertEqual(check.call_count, 2)

    def test_watchdog_rejects_unbound_review(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / review.VIDEO).write_bytes(b"video")
            (root / "QA.md").write_text("QA")
            review.save(root / review.REPORT, {"sha256": "wrong"})
            review.save(root / "RIGHTS_EVIDENCE.json", {})
            self.assertIn("불일치", inspect_artifact(root, review.VIDEO, review.REPORT))

    def test_trend_selection_uses_matching_catalog_keywords(self):
        self.assertEqual(trend_matches("놀라운 번개 장면 TOP5", ["축구", "서울 낙뢰"]),
                         ["서울 낙뢰"])

    def test_domino_query_rejects_falling_objects_and_jenga(self):
        topic = "신기한 도미노 장면 TOP5"
        self.assertTrue(obvious_topic_mismatch("diamonds, rain, falling", topic))
        self.assertTrue(obvious_topic_mismatch("jenga, blocks, domino", topic))
        self.assertFalse(obvious_topic_mismatch("dominoes, game, tiles, falling", topic))

    def test_machinery_query_rejects_abstract_graphics_and_counter(self):
        topic = "만족스러운 기계 움직임 TOP5"
        self.assertTrue(obvious_topic_mismatch("gear, industry, machine, abstract, doodle", topic))
        self.assertTrue(obvious_topic_mismatch("numbers, counter, mechanical, scoreboard", topic))
        self.assertTrue(obvious_topic_mismatch("cylinders, mechanical, engine, wallpaper", topic))
        self.assertTrue(obvious_topic_mismatch("steampunk, clock, gears, time machine, fantasy", topic))
        self.assertFalse(obvious_topic_mismatch("field, machinery, combine, agriculture", topic))

    def test_original_topic_shortfall_preserved_after_fallback(self):
        def fake_download(key, plan, work, **kwargs):
            topic = plan["selected"]["topic"]
            rows = []
            if topic == "폭포":
                for index in range(5):
                    name = f"source_{index}.mp4"
                    (work / name).write_bytes(bytes([index]))
                    rows.append({"file": name})
            return {"status": "PASS" if rows else "BLOCKED", "downloaded_valid_sources": len(rows),
                    "sources": rows, "failures": []}

        plan = {"selected": {"topic": "도미노", "search_queries": ["domino"]},
                "alternatives": [{"topic": "폭포", "search_queries": ["waterfall"]}]}
        with TemporaryDirectory() as folder:
            out = Path(folder)
            with patch("top5_free_source_download.inspect", side_effect=fake_download):
                report = acquire(None, None, plan, out, {}, None, {}, 2)
            self.assertEqual(plan["selected"]["topic"], "폭포")
            self.assertEqual([item["downloaded_valid_sources"] for item in report["topic_attempts"]], [0, 5])
            self.assertTrue(all((out / row["file"]).exists() for row in report["sources"]))

    def test_audio_repair_rechecks_candidate_and_stops_on_repeat(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source_dir = root / "sources"
            source_dir.mkdir()
            plan = root / "plan.json"
            review.save(plan, {"selected": {"topic": "테스트 TOP5"}})
            review.save(source_dir / "SOURCE_DOWNLOAD_QA.json",
                        {"sources": [{"sha256": str(index), "cut_start_sec": 0, "duration_sec": 6}
                                     for index in range(5)]})
            checks = [{"audio": False}, {"audio": False}]
            with (patch.object(review, "source_issue", return_value=None),
                  patch.object(review, "render_parts", return_value=root / "concat.txt"),
                  patch.object(review, "mux") as mux,
                  patch.object(review, "verify_media", side_effect=checks) as verify):
                with self.assertRaises(SystemExit):
                    review.produce(plan, source_dir, root)
            self.assertEqual(verify.call_count, 2)
            self.assertEqual([call.args[2] for call in mux.call_args_list], [4, 7])
            self.assertFalse((root / review.VIDEO).exists())
            self.assertEqual(review.read(root / review.REPORT)["status"], "TECHNICAL_FAILED")

    def test_verified_editorial_replacement_is_bound_to_clip_and_reserve(self):
        def source(index):
            return {"sha256": str(index), "page_url": f"https://example.com/{index}",
                    "cut_start_sec": 0, "creator": f"creator {index}"}

        sources = [source(i) for i in range(5)]
        reserves = [source(6)]
        clips = [{"rank": 5-i, "source_sha256": row["sha256"], "source_start_sec": 0,
                  "source_page": row["page_url"], "verified": True,
                  "editorial_score": 50 if i == 0 else 85} for i, row in enumerate(sources)]
        candidate = {"source_sha256": "6", "source_start_sec": 0, "source_page": reserves[0]["page_url"],
                     "editorial_reviewed": True, "rights_independently_cleared": True,
                     "creator": reserves[0]["creator"], "license_evidence_url": "https://example.com/license",
                     "editorial_score": 80}
        qa = {"clips": clips, "replacement_candidates": [candidate]}
        with patch.object(review, "source_issue", return_value=None):
            revised, repairs = review.editorial_replacements(sources, reserves, qa, Path("."), {}, 0)
            self.assertEqual(revised[0]["sha256"], "6")
            self.assertEqual(repairs[0]["code"], "VERIFIED_EDITORIAL_BELOW_75")
            candidate["source_start_sec"] = 3
            self.assertIsNone(review.editorial_replacements(sources, reserves, qa, Path("."), {}, 0))

    def test_source_guards_are_ordered_and_fail_closed(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            path = directory / "clip.mp4"
            path.write_bytes(b"source evidence")
            row = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "page_url": "https://example.com/source", "tags": "dominoes",
                   "query": "domino", "cut_start_sec": 0, "duration_sec": 10}
            selected = {"topic": "도미노", "search_queries": ["domino"]}
            self.assertIsNone(review.source_issue(row, directory, selected, []))
            self.assertEqual(review.source_issue(row, directory, selected, [row]), "SOURCE_DUPLICATE")
            self.assertEqual(review.source_issue(dict(row, tags="rain"), directory, selected, []),
                             "SOURCE_TOPIC_MISMATCH")
            self.assertEqual(review.source_issue(dict(row, cut_start_sec=5), directory, selected, []),
                             "CUT_DURATION")
            path.write_bytes(b"changed")
            self.assertEqual(review.source_issue(row, directory, selected, []), "SOURCE_INTEGRITY")


if __name__ == "__main__":
    unittest.main()
