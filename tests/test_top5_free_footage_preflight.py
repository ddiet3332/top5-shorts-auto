import importlib.util,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"src";sys.path.insert(0,str(root))
from top5_free_footage_preflight import evaluate
class PreflightTests(unittest.TestCase):
 def test_rejects_animation_and_duplicates(self):
  import top5_free_footage_preflight as m
  old=m.collect
  def fake(key,query):
   return {"candidates":[{"id":1,"tags":"cartoon dog","duration":9,"has_video_variant":True},{"id":2,"tags":"nature","duration":7,"has_video_variant":True},{"id":3,"tags":"nature","duration":2,"has_video_variant":True}]}
  m.collect=fake
  try:
   r=evaluate({"selected":{"topic":"test","category":"nature","search_queries":["a","b"]}},"fake")
   self.assertEqual(r["metadata_candidates"],1)
   self.assertFalse(r["eligible_for_download"])
   self.assertFalse(r["publication_approved"])
  finally:m.collect=old
if __name__=="__main__":unittest.main()
