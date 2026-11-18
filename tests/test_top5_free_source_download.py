import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import top5_free_source_download as m
class SourceDownloadTests(unittest.TestCase):
 def test_five_distinct_sources_with_audit(self):
  old=(m.download,m.probe,m.decode)
  try:
   m.download=lambda url,path,max_bytes: path.write_bytes(b"test")
   m.probe=lambda path:6.0
   m.decode=lambda path:None
   hits=[{"id":i,"tags":"nature","duration":8,"videos":{"medium":{"url":"https://cdn.pixabay.com/a.mp4"}},"pageURL":"https://pixabay.com/videos/example","user":"creator"} for i in range(1,6)]
   with tempfile.TemporaryDirectory() as d:
    r=m.inspect("fake",{"selected":{"topic":"폭포","category":"nature","search_queries":["waterfall"]}},Path(d),fetch=lambda key,q:hits)
    self.assertEqual(r["downloaded_valid_sources"],5)
    self.assertTrue(all(x["editorial_score"] is None for x in r["sources"]))
    self.assertFalse(r["publication_approved"])
    self.assertTrue((Path(d)/"SOURCE_DOWNLOAD_QA.json").exists())
  finally:m.download,m.probe,m.decode=old
if __name__=="__main__":unittest.main()
