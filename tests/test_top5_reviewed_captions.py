import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_generic_v06_preview import load_reviewed_captions
class TestReviewedCaptions(unittest.TestCase):
 def test_reject_unverified_and_mismatch(self):
  sources=[{"id":i} for i in range(5)]
  entries=[{"source_id":i,"rank_name":"꽃 위의 나비","caption":"꽃 위에 앉아 있는 나비"} for i in range(5)]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"review.json"
   p.write_text(json.dumps({"verified_by_human":False,"entries":entries}))
   with self.assertRaises(ValueError):load_reviewed_captions(p,sources)
   p.write_text(json.dumps({"verified_by_human":True,"entries":entries}))
   self.assertEqual(len(load_reviewed_captions(p,sources)),5)
   entries[0]["source_id"]=99
   p.write_text(json.dumps({"verified_by_human":True,"entries":entries}))
   with self.assertRaises(ValueError):load_reviewed_captions(p,sources)
 def test_no_review_returns_none(self):
  self.assertIsNone(load_reviewed_captions(None,[]))
if __name__=="__main__":unittest.main()
