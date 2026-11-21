import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dog_commons_discovery import classify_title, discover_commons, trusted

def video(title="File:Dog jumping over a toy.webm", **overrides):
    row = {
        "title": title,
        "source_page": "https://commons.wikimedia.org/wiki/File:Dog_jumping_over_a_toy.webm",
        "download_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Dog.webm",
        "author": "Filmmaker",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "size_bytes": 500000,
    }
    row.update(overrides)
    return row


class CommonsDiscoveryTests(unittest.TestCase):
    def test_action_and_dog_relevance(self):
        self.assertEqual(classify_title("File:Dog jumping.webm"), "jump")
        self.assertEqual(classify_title("File:Puppy surprise.webm"), "surprise")
        self.assertIsNone(classify_title("File:Cat jumping.webm"))
        self.assertIsNone(classify_title("File:Dog cartoon jumping.webm"))

    def test_dedup_and_rights_fail_closed(self):
        eligible = video()
        wrong = video("File:Dog falling.webm",
                      license_url="https://creativecommons.org/licenses/by-nc/4.0/")
        fake = video("File:Puppy jumping.webm",
                     download_url="https://upload.wikimedia.org.evil.invalid/file.webm")
        result = discover_commons(
            search=lambda term, per_query: [eligible, wrong, fake],
            categories=lambda term, per_query: [eligible],
            max_results=10)
        self.assertEqual(result["status"], "CANDIDATES_FOUND")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["action_family_from_title"], "jump")
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["candidates"][0]["rights_status"], "UNVERIFIED")
        self.assertIn("download_url", result["candidates"][0])

    def test_fail_closed_if_search_down(self):
        def fail(*args, **kwargs):
            raise RuntimeError("network down")
        result = discover_commons(search=fail, categories=fail)
        self.assertEqual(result["status"], "SOURCE_REQUEST_FAILED")
        self.assertEqual(len(result["errors"]), 9)
        self.assertEqual(result["candidates"], [])

    def test_untrusted_hostname_and_overlarge(self):
        self.assertFalse(trusted(video(source_page="https://commons.wikimedia.org.evil.test/file")))
        self.assertFalse(trusted(video(size_bytes=60 * 1024 * 1024)))


if __name__ == "__main__":
    unittest.main()
