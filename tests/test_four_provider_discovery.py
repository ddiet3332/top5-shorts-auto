import unittest
from src.four_provider_discovery import run
class TestFourProvider(unittest.TestCase):
    def test_missing_keys_do_not_block_public_providers(self):
        result=run({"candidates":[{"id":"a","source_url":"https://commons.wikimedia.org/wiki/File:A.webm"}]},{"candidates":[{"id":"b","source_url":"https://archive.org/details/b"}]})
        self.assertEqual(result["count"],2)
        self.assertEqual(result["providers"]["pexels"]["status"],"SKIP_MISSING_API_KEY")
        self.assertEqual(result["providers"]["pixabay"]["status"],"SKIP_MISSING_API_KEY")
        self.assertFalse(result["publication_approved"])
    def test_dedup_and_provider_error_isolation(self):
        def broken(_): raise OSError("network")
        result=run({"candidates":[{"id":"a","source_url":"https://commons.wikimedia.org/wiki/File:A.webm"}]*2},{"candidates":[]},pexels_key="test",pexels_reader=broken)
        self.assertEqual(result["count"],1)
        self.assertEqual(result["providers"]["pexels"]["status"],"PROVIDER_ERROR")
    def test_four_provider_normalization(self):
        def p(_): return {"status":"DISCOVERY_ONLY","candidates":[{"provider":"pexels","id":"1","source_url":"https://www.pexels.com/video/1","rights_verified":False}]}
        def x(_): return {"status":"DISCOVERY_ONLY","candidates":[{"provider":"pixabay","id":"2","source_url":"https://pixabay.com/videos/id-2/","rights_verified":False}]}
        result=run({"candidates":[]},{"candidates":[]},pexels_key="a",pixabay_key="b",pexels_reader=p,pixabay_reader=x)
        self.assertEqual(result["count"],2)
        self.assertTrue(all(not x["publication_approved"] for x in result["candidates"]))
if __name__=="__main__":unittest.main()
