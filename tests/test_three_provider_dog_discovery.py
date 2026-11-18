import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from three_provider_dog_discovery import aggregate,pexels_collect,commons_collect

class ThreeProviderTest(unittest.TestCase):
    def test_fail_closed_and_deduplicate(self):
        pools={"pexels":{"status":"METADATA_ONLY","candidates":[{"id":1,"page_url":"https://www.pexels.com/video/test-1/"}]*2},
               "pixabay":{"status":"METADATA_ONLY","candidates":[{"id":1,"page_url":"https://pixabay.com/videos/test-1/"}]},
               "wikimedia":{"status":"ERROR_HTTPError","candidates":[]}}
        result=aggregate(pools)
        self.assertEqual(len(result["candidates"]),2)
        self.assertFalse(result["publication_approved"])
        self.assertTrue(all(not x["rights_verified"] and not x["approved_for_publication"] for x in result["candidates"]))
    def test_pexels_without_key(self):
        self.assertEqual(pexels_collect("","dog")["status"],"SKIPPED_NO_SECRET")
    def test_pexels_metadata_only(self):
        def fake(url,headers):
            self.assertEqual(headers["Authorization"],"example")
            return {"videos":[{"id":5,"url":"https://www.pexels.com/video/dog-5/","duration":9}]}
        result=pexels_collect("example","funny puppy",fake)
        self.assertEqual(result["candidates"][0]["id"],5)
    def test_commons_metadata_only(self):
        def fake(url):
            return {"query":{"pages":[{"pageid":3,"title":"File:Dog.webm","imageinfo":[{"mime":"video/webm","extmetadata":{"LicenseUrl":{"value":"https://creativecommons.org/licenses/by/4.0/"}}}]}]}}
        result=commons_collect("dog",fake)
        self.assertFalse(result["candidates"][0]["approved_for_publication"])
if __name__=="__main__": unittest.main()
