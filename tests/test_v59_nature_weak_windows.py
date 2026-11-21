"""V59: real V58 frames rejected only for two exact weak nature source windows.

No semantic scoring, broad provider ban, or copyright/YPP approval is implied.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_auto_v30 import reviewed_weak_window

WEAK_V58 = (
    (
        "File:2022-01-11 Garonne River Overflow 5472.webm",
        "e81e2fe53870c48f2b0f58cd7043dfd3458344f8f93f81e7d1efa0b1398f7964",
        6.0,
    ),
    (
        "File:Side view video of Kawaida Waterfall cascading, Cianda, Kiambu County.webm",
        "8154f19f4c593f7af6021a919a079a8b4ef741d3d09fb7726033b4d157a6b7dc",
        2.0,
    ),
)


class V59NatureWeakWindowTests(unittest.TestCase):
    def test_exact_v58_weak_windows_rejected(self):
        for title, sha, start in WEAK_V58:
            with self.subTest(title=title):
                reason = reviewed_weak_window("nature_moments", title, sha, start)
                self.assertIsInstance(reason, str)
                self.assertIn("V58 main auto92", reason)

    def test_time_bounds_but_not_other_cuts(self):
        for title, sha, start in WEAK_V58:
            with self.subTest(title=title):
                self.assertIsNotNone(reviewed_weak_window(
                    "nature_moments", title, sha, start + 0.21))
                self.assertIsNone(reviewed_weak_window(
                    "nature_moments", title, sha, start + 0.23))
                self.assertIsNone(reviewed_weak_window(
                    "nature_moments", title, sha, max(0.0, start - 0.24)))

    def test_different_source_bytes_not_rejected(self):
        for title, sha, start in WEAK_V58:
            with self.subTest(title=title):
                changed_sha = ("0" if sha[0] != "0" else "1") + sha[1:]
                self.assertIsNone(reviewed_weak_window(
                    "nature_moments", title, changed_sha, start))

    def test_title_and_topic_also_required(self):
        for title, sha, start in WEAK_V58:
            with self.subTest(title=title):
                self.assertIsNone(reviewed_weak_window(
                    "cat_surprises", title, sha, start))
                self.assertIsNone(reviewed_weak_window(
                    "nature_moments", "Different nature original.webm", sha, start))


if __name__ == "__main__":
    unittest.main()
