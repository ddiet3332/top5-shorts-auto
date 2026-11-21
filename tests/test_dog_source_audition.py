"""Offline tests for bounded audition and publication safety."""
import json
import os
from unittest.mock import patch
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_source_audition import audition


class DogAuditionTests(unittest.TestCase):
    def test_preview_keeps_rights_unverified_and_deletes_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            discovery = root / "discovery.json"
            discovery.write_text(json.dumps({"candidates": [
                {"id": "PX-123", "source_url": "https://www.pexels.com/video/dog-123/",
                 "creator": "Maker"}]}))
            def fake_download(source, dest, max_bytes):
                self.assertEqual(max_bytes, 35 * 1024 * 1024)
                dest.write_bytes(b"test media")
                return {"duration_sec": 8}
            def fake_preview(source, start, dest):
                dest.write_bytes(b"preview")
            out = root / "out"
            result = audition(discovery, out, downloader=fake_download, previewer=fake_preview)
            row = result["candidates"][0]
            self.assertEqual(row["status"], "PREVIEW_READY_REVIEW_REQUIRED")
            self.assertEqual(row["rights_status"], "UNVERIFIED")
            self.assertFalse(row["publication_approved"])
            self.assertTrue((out / row["preview_file"]).exists())
            self.assertFalse((out / "PX-123.mp4").exists())

    def test_rotates_candidates_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            discovery = root / "discovery.json"
            discovery.write_text(json.dumps({"candidates": [
                {"id": f"PX-{i}", "source_url": f"https://www.pexels.com/video/dog-{i}/",
                 "creator": "Maker"} for i in (100, 101, 102, 103)]}))
            def fake_download(source, dest, max_bytes):
                dest.write_bytes(b"test")
                return {"duration_sec": 8}
            def fake_preview(source, start, dest):
                dest.write_bytes(b"preview")
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "5"}):
                result = audition(discovery, root / "out", downloader=fake_download,
                                  previewer=fake_preview)
            self.assertEqual([r["id"] for r in result["candidates"]], ["PX-101", "PX-102"])

    def test_rejects_unbounded_audition(self):
        with self.assertRaises(ValueError):
            audition(Path("missing"), Path("unused"), max_items=4)


if __name__ == "__main__":
    unittest.main()
