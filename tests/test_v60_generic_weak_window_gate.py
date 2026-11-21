"""V60: exact reviewed dog cuts cannot silently recur in generic TOP5 production."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import top5_free_source_download as dl
import top5_production_review as production
from top5_v60_weak_generic_window_gate import reviewed_weak_generic_window, REASON, REGISTRY


class GenericWeakWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["rejected_windows"]

    def test_all_five_real_v59_rank_cuts_match(self):
        self.assertEqual(len(self.entries), 5)
        self.assertEqual({row["observed_rank"] for row in self.entries}, {1, 2, 3, 4, 5})
        for item in self.entries:
            source = dict(provider=item["provider"], id=item["source_id"],
                          sha256=item["sha256"], page_url=item["source_page"])
            with self.subTest(rank=item["observed_rank"]):
                self.assertIsInstance(
                    reviewed_weak_generic_window(item["topic"], source, item["source_start_sec"]), str)
                self.assertIsNone(reviewed_weak_generic_window(
                    item["topic"], source, item["source_start_sec"] + 0.13))
                self.assertIsNone(reviewed_weak_generic_window(
                    item["topic"], source, max(0, item["source_start_sec"] - 0.13)
                ) if item["source_start_sec"] >= 0.13 else reviewed_weak_generic_window(
                    item["topic"], source, item["source_start_sec"] + 0.25))
                self.assertIsNone(reviewed_weak_generic_window(
                    "고양이의 예상 밖 행동 TOP5", source, item["source_start_sec"]))
                self.assertIsNone(reviewed_weak_generic_window(
                    item["topic"], {**source, "sha256": "a"*64}, item["source_start_sec"]))
                self.assertIsNone(reviewed_weak_generic_window(
                    item["topic"], {**source, "page_url": "https://example.com/other"}, item["source_start_sec"]))
                self.assertIsNone(reviewed_weak_generic_window(
                    item["topic"], {**source, "id": "999999"}, item["source_start_sec"]))

    def test_preparation_rejects_real_original_before_technical_motion_heuristic(self):
        weak = self.entries[0]
        source = dict(topic=weak["topic"], provider=weak["provider"], id=weak["source_id"],
                      sha256=weak["sha256"], page_url=weak["source_page"], duration_sec=20)
        with (patch.object(production, "select_start", return_value=weak["source_start_sec"]),
              patch.object(production, "motion") as motion):
            with self.assertRaisesRegex(ValueError, REASON):
                production.prepare_source(Path("original-not-needed.mp4"), source, [])
            motion.assert_not_called()

    def test_existing_acquisition_cannot_render_known_weak_cut(self):
        weak = self.entries[0]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "original.mp4"
            path.write_bytes(b"actual sha cannot be forged for this test")
            source = dict(id=weak["source_id"], provider=weak["provider"],
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          file=path.name, page_url=weak["source_page"],
                          cut_start_sec=weak["source_start_sec"], duration_sec=20)
            with patch.object(production, "reviewed_weak_generic_window", return_value="weak"):
                self.assertEqual(production.source_issue(
                    source, root, {"topic": weak["topic"], "search_queries": []}, []), REASON)

    def test_weak_candidate_is_skipped_and_later_five_fill_rank_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            topic = "강아지의 웃긴 행동 TOP5"
            candidates = [
                dict(id=n, tags="funny, dog, puppy, playing", duration=10,
                     user="author_"+str(n),
                     pageURL=f"https://pixabay.com/videos/id-{n}/",
                     videos={"medium": {"url": f"https://cdn.pixabay.com/{n}.mp4"}})
                for n in [77509, 81001, 81002, 81003, 81004, 81005]
            ]
            fake_hash = hashlib.sha256(b"source-id-77509").hexdigest()
            registry = root / "exact.json"
            weak = dict(self.entries[0])
            weak["sha256"] = fake_hash
            weak["source_start_sec"] = 0
            registry.write_text(json.dumps({"rejected_windows": [weak]}), encoding="utf-8")
            def fake_download(url, path, max_bytes):
                path.write_bytes(("source-id-" + Path(url).stem).encode())
            def scoped_gate(actual_topic, source, start=None):
                return reviewed_weak_generic_window(
                    actual_topic, source, start, registry_path=registry)
            with (patch.object(dl, "download", side_effect=fake_download),
                  patch.object(dl, "probe", return_value=10.0),
                  patch.object(dl, "decode"),
                  patch.object(production, "select_start", return_value=0),
                  patch.object(production, "motion", return_value={"peak_change": 15, "mean_change": 5, "sample_count": 24}),
                  patch.object(production, "frame_signature", side_effect=lambda p, t: (int(Path(p).stem.split("_")[-1]), 120)),
                  patch.object(production, "similar_frames", return_value=False),
                  patch.object(production, "reviewed_weak_generic_window", side_effect=scoped_gate)):
                result = dl.inspect(
                    "fake-key",
                    {"selected": {"topic": topic, "category": "animals",
                                  "search_queries": ["funny dog playing"]}},
                    root, fetch=lambda key, query: candidates,
                    prepare=production.prepare_source)
            self.assertEqual(result["downloaded_valid_sources"], 5)
            self.assertEqual(result["reviewed_weak_window_rejections"], 1)
            self.assertNotIn(77509, {x["id"] for x in result["sources"]})
            self.assertEqual([x["id"] for x in result["sources"]],
                             [81001, 81002, 81003, 81004, 81005])
            self.assertFalse(result["publication_approved"])
            self.assertTrue(any(REASON in item["reason"] for item in result["failures"]))


if __name__ == "__main__":
    unittest.main()
