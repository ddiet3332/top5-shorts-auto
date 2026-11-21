import sys
import unittest
import urllib.error
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_pixabay_discovery import discover_pixabay, cached_pixabay

class PixabayDiscoveryTests(unittest.TestCase):
    def test_all_http_failures_are_not_source_shortage(self):
        def fail(_url):
            raise urllib.error.HTTPError("https://pixabay.com/api/videos/", 403, "Forbidden", {}, None)
        result=discover_pixabay("mock",fetch=fail)
        self.assertEqual(result["status"],"API_REQUEST_FAILED")
        self.assertEqual(len(result["errors"]),1)  # 403 must stop further API requests
        self.assertTrue(all(item["http_status"]==403 for item in result["errors"]))
        self.assertFalse(result["publication_approved"])

    def test_access_denied_stops_extra_requests(self):
        requests=[]
        def fail(url):
            requests.append(url)
            raise urllib.error.HTTPError("https://pixabay.com/api/videos/",403,"Forbidden",{},None)
        result=discover_pixabay("mock",fetch=fail)
        self.assertEqual(result["status"],"API_REQUEST_FAILED")
        self.assertEqual(len(requests),1)
        self.assertEqual(result["errors"][0]["http_status"],403)

    def test_reuse_cache_for_full_24_hours_and_manual_refresh(self):
        with tempfile.TemporaryDirectory() as temp:
            cache=Path(temp)/"discovery.json"
            calls=[]
            def discover(_key):
                calls.append(1)
                return {"status":"API_REQUEST_FAILED","provider":"pixabay",
                        "candidates":[],"errors":[{"http_status":403}],
                        "publication_approved":False}
            first=cached_pixabay("key",cache,now=100000,discover=discover)
            self.assertEqual(first["cache_status"],"REFRESHED")
            self.assertEqual(cached_pixabay("key",cache,now=100000+86399,
                                            discover=discover)["cache_status"],"REUSED_24H")
            self.assertEqual(len(calls),1)
            self.assertEqual(cached_pixabay("key",cache,now=100000+86400,
                                            discover=discover)["cache_status"],"REFRESHED")
            self.assertEqual(len(calls),2)
            self.assertEqual(cached_pixabay("key",cache,force=True,now=200000,
                                            discover=discover)["cache_status"],"REFRESHED")
            self.assertEqual(len(calls),3)
            self.assertNotIn("key",cache.read_text(encoding="utf-8"))

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
    def test_media_urls_are_transient_not_in_discovery_evidence(self):
        hit={"id":345,"duration":10,"pageURL":"https://pixabay.com/videos/dog-345/",
             "user":"creator","tags":"happy dog, playful",
             "videos":{"medium":{"url":"https://cdn.pixabay.com/video/345.mp4","width":720,"height":1280}}}
        media={}
        result=discover_pixabay("mock",fetch=lambda url:{"hits":[hit]},transient_media=media)
        self.assertEqual(media,{"PB-345":"https://cdn.pixabay.com/video/345.mp4"})
        self.assertEqual(len(result["candidates"]),1)
        self.assertNotIn("video_url",result["candidates"][0])
        self.assertNotIn("cdn.pixabay.com",str(result))
        self.assertEqual(result["candidates"][0]["tags_from_provider"],"happy dog, playful")

    def test_obvious_green_screen_source_is_not_treated_as_real_dog(self):
        hit={"id":345,"duration":10,"pageURL":"https://pixabay.com/videos/dog-345/",
             "user":"GreenScreenFX","videos":{"medium":{"url":"https://cdn.pixabay.com/test.mp4"}}}
        self.assertEqual(discover_pixabay("mock",fetch=lambda _:{"hits":[hit]})["candidates"],[])

    def test_reject_bad_page_and_exclusion(self):
        hit={"id":123,"duration":9,"pageURL":"https://evil.example/video",
             "videos":{"medium":{"url":"https://evil.example/file.mp4"}}}
        self.assertEqual(discover_pixabay("mock",fetch=lambda url:{"hits":[hit]})["candidates"],[])
        hit["pageURL"]="https://pixabay.com/videos/dog-123/"
        self.assertEqual(discover_pixabay("mock",fetch=lambda url:{"hits":[hit]},excluded_ids=[123])["candidates"],[])
if __name__=="__main__":
    unittest.main()
