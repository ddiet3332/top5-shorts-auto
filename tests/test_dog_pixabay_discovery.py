import sys
import unittest
import urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_pixabay_discovery import discover_pixabay

class PixabayDiscoveryTests(unittest.TestCase):
    def test_all_http_failures_are_not_source_shortage(self):
        def fail(_url):
            raise urllib.error.HTTPError("https://pixabay.com/api/videos/", 403, "Forbidden", {}, None)
        result=discover_pixabay("mock",fetch=fail)
        self.assertEqual(result["status"],"API_REQUEST_FAILED")
        self.assertEqual(len(result["errors"]),3)
        self.assertTrue(all(item["http_status"]==403 for item in result["errors"]))
        self.assertFalse(result["publication_approved"])

    def test_missing_key(self):
        self.assertEqual(discover_pixabay("")["status"],"NO_API_KEY")
    def test_unique_and_unverified(self):
        hit={"id":123,"duration":9,"pageURL":"https://pixabay.com/videos/test-123/",
             "user":"creator","videos":{"medium":{"url":"https://cdn.pixabay.com/video.mp4","width":720,"height":1280}}}
        result=discover_pixabay("mock",fetch=lambda url:{"hits":[hit]})
        self.assertEqual(len(result["candidates"]),1)
        self.assertEqual(result["candidates"][0]["id"],"PB-123")
        self.assertEqual(result["candidates"][0]["rights_status"],"UNVERIFIED")
        self.assertFalse(result["publication_approved"])
        self.assertNotIn("video_url",result["candidates"][0])
    def test_reject_bad_page_and_exclusion(self):
        hit={"id":123,"duration":9,"pageURL":"https://evil.example/video",
             "videos":{"medium":{"url":"https://evil.example/file.mp4"}}}
        self.assertEqual(discover_pixabay("mock",fetch=lambda url:{"hits":[hit]})["candidates"],[])
        hit["pageURL"]="https://pixabay.com/videos/dog-123/"
        self.assertEqual(discover_pixabay("mock",fetch=lambda url:{"hits":[hit]},excluded_ids=[123])["candidates"],[])
if __name__=="__main__":
    unittest.main()
