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
   hits=[{"id":i,"tags":"waterfall, river, nature","duration":8,"videos":{"medium":{"url":"https://cdn.pixabay.com/a.mp4"}},"pageURL":"https://pixabay.com/videos/example","user":"creator"+str((i-1)//2)} for i in range(1,6)]
   with tempfile.TemporaryDirectory() as d:
    r=m.inspect("fake",{"selected":{"topic":"폭포","category":"nature","search_queries":["waterfall"]}},Path(d),fetch=lambda key,q:hits)
    self.assertEqual(r["downloaded_valid_sources"],5)
    self.assertLessEqual(max(r["creator_counts"].values()),2)
    self.assertTrue(all(x["editorial_score"] is None for x in r["sources"]))
    self.assertFalse(r["publication_approved"])
    self.assertTrue((Path(d)/"SOURCE_DOWNLOAD_QA.json").exists())
  finally:m.download,m.probe,m.decode=old
 def test_two_queries_are_balanced(self):
  old=(m.download,m.probe,m.decode)
  try:
   m.download=lambda url,path,max_bytes: path.write_bytes(b"test")
   m.probe=lambda path:6.0
   m.decode=lambda path:None
   def fetch(key,q):
    base=1 if q=="funny dog playing" else 101
    return [{"id":base+i,"tags":"funny, dog, puppy, playful, playing","duration":8,"videos":{"medium":{"url":"https://cdn.pixabay.com/a.mp4"}},"pageURL":"https://pixabay.com/videos/example","user":"creator"+str(i)} for i in range(8)]
   with tempfile.TemporaryDirectory() as d:
    r=m.inspect("fake",{"selected":{"topic":"강아지의 웃긴 행동 TOP5","category":"animals","search_queries":["funny dog playing","playful puppy"]}},Path(d),fetch=fetch)
    self.assertEqual(r["downloaded_valid_sources"],5)
    self.assertEqual(r["query_counts"]["funny dog playing"],3)
    self.assertEqual(r["query_counts"]["playful puppy"],2)
  finally:m.download,m.probe,m.decode=old
 def test_rejected_source_replaced_from_later_candidates(self):
  old=(m.download,m.probe,m.decode)
  try:
   m.download=lambda url,path,max_bytes:path.write_bytes(b"test")
   m.probe=lambda path:6.0
   m.decode=lambda path:None
   def fetch(key,q):
    base=1 if q=="waterfall aerial" else 101
    return [{"id":base+i,"tags":"waterfall, river, aerial, beautiful","duration":8,"videos":{"medium":{"url":"https://cdn.pixabay.com/a.mp4"}},"pageURL":"https://pixabay.com/videos/example","user":"creator"+str(i)} for i in range(8)]
   with tempfile.TemporaryDirectory() as d:
    r=m.inspect("fake",{"selected":{"topic":"폭포의 장관 TOP5","category":"nature","search_queries":["waterfall aerial","beautiful waterfall"]}},Path(d),fetch=fetch,rejected={1,2,101})
    self.assertEqual(r["downloaded_valid_sources"],5)
    self.assertFalse({1,2,101}.intersection({s["id"] for s in r["sources"]}))
    self.assertEqual(r["query_counts"]["waterfall aerial"],3)
    self.assertEqual(r["query_counts"]["beautiful waterfall"],2)
  finally:m.download,m.probe,m.decode=old
 def test_creator_cap(self):
  self.assertTrue(m.creator_allowed("A",{"A":1}))
  self.assertFalse(m.creator_allowed("A",{"A":2}))
  self.assertFalse(m.creator_allowed("",{}))
if __name__=="__main__":unittest.main()
