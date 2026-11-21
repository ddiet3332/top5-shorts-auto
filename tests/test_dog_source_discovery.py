"""Mocked discovery tests; no external requests or secrets required."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_source_discovery import discover


class DogDiscoveryTests(unittest.TestCase):
    def test_no_key_fails_closed(self):
        result = discover("")
        self.assertEqual(result["status"], "NO_API_KEY")
        self.assertFalse(result["publication_approved"])

    def test_deduplicates_and_never_clears_rights(self):
        calls = []
        def fake_fetch(url, key):
            calls.append(url)
            return {"videos": [{"id": 123, "url": "https://www.pexels.com/video/test-123/",
                                "duration": 9, "width": 1080, "height": 1920,
                                "user": {"name": "Maker"}}]}
        result = discover("test-key", fetch=fake_fetch)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["rights_status"], "UNVERIFIED")
        self.assertEqual(result["candidates"][0]["semantic_review"], "UNVERIFIED")
        self.assertEqual(len(calls), 3)

    def test_limits_and_bad_source_rejected(self):
        with self.assertRaises(ValueError):
            discover("test-key", per_page=100)
        result = discover("test-key", fetch=lambda u, k: {"videos": [
            {"id": 1, "url": "https://untrusted.example/video", "duration": 9}]})
        self.assertEqual(result["status"], "SOURCE_SHORTAGE")


if __name__ == "__main__":
    unittest.main()
