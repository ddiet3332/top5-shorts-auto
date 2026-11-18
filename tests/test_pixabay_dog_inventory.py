import io
import json
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pixabay_dog_inventory import collect

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return self.payload
    def __init__(self, obj): self.payload = json.dumps(obj).encode()
    
class PixabayInventoryTest(unittest.TestCase):
    def test_missing_key_fails_closed(self):
        with self.assertRaises(ValueError):
            collect("", "funny dog")
    def test_metadata_never_approves_rights(self):
        def fake_open(request, timeout):
            self.assertIn("q=funny+dog", request.full_url)
            self.assertIn("key=test-secret", request.full_url)
            return FakeResponse({"hits":[{"id":42,"pageURL":"https://pixabay.com/videos/example-42/","user":"maker","tags":"dog, funny","duration":8,"videos":{"medium":{"url":"https://cdn.pixabay.com/video.mp4","width":640,"height":360}}}]})
        result = collect("test-secret", "funny dog", opener=fake_open)
        self.assertEqual(result["count"], 1)
        item = result["candidates"][0]
        self.assertFalse(item["approved_for_publication"])
        self.assertFalse(item["rights_verified"])
        self.assertNotIn("download_url", item)
        self.assertNotIn("test-secret", json.dumps(result))
if __name__ == "__main__": unittest.main()
