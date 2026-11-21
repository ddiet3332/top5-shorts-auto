import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dog_commons_audition import audition_commons, download_commons

def candidate():
    return {
        "id": "CM-012345abcdef", "provider": "wikimedia_commons",
        "source_title": "File:Dog jumping.webm",
        "source_url": "https://commons.wikimedia.org/wiki/File:Dog_jumping.webm",
        "download_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Dog.webm",
        "creator": "Filmmaker", "size_bytes": 100000,
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "action_family_from_title": "jump",
    }


class CommonsAuditionTests(unittest.TestCase):
    def test_candidate_preview_only_never_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            discovered = root / "discovered.json"
            discovered.write_text(json.dumps({"candidates":[candidate()]}), encoding="utf-8")
            out = root / "output"
            def fake_download(item, target):
                target.write_bytes(b"video" * 1000)
            def fake_preview(source, start, target):
                target.write_bytes(b"preview" * 1000)
            result = audition_commons(discovered, out,
                downloader=fake_download, probe=lambda _p: 12.0,
                motion=lambda *_args, **_kwargs: (2.0, 5.0),
                previewer=fake_preview, run_id="123")
            self.assertEqual(result["status"], "PREVIEW_READY")
            self.assertEqual(result["candidates"][0]["status"], "PREVIEW_READY_REVIEW_REQUIRED")
            self.assertFalse(result["publication_approved"])
            self.assertFalse(result["candidates"][0]["reviewed_frames"])
            self.assertFalse((out / "CM-012345abcdef.webm").exists())
            self.assertTrue((out / "CM-012345abcdef_preview.mp4").exists())

    def test_unsafe_url_rejected_without_network(self):
        row = candidate()
        row["download_url"] = "https://upload.wikimedia.org.evil.invalid/video.webm"
        with tempfile.TemporaryDirectory() as temp:
            def unexpected(*args, **kwargs):
                raise AssertionError("network call not allowed")
            with self.assertRaises(ValueError):
                download_commons(row, Path(temp) / "test.webm", opener=unexpected)

    def test_still_video_not_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = root / "d.json"
            d.write_text(json.dumps({"candidates":[candidate()]}))
            result = audition_commons(d, root / "out",
                downloader=lambda item, target: target.write_bytes(b"a" * 5000),
                probe=lambda _: 9.0, motion=lambda *_a, **_k: (0.0, 0.0),
                previewer=lambda *_: None)
            self.assertEqual(result["status"], "NO_PREVIEW")
            self.assertEqual(result["candidates"][0]["status"], "AUDITION_FAILED")
            self.assertFalse(result["publication_approved"])


if __name__ == "__main__":
    unittest.main()
