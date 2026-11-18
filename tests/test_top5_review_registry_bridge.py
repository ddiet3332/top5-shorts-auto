import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_review_registry_bridge import build
class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.qa={"topic":"test TOP5","sources":[{"id":i,"provider":"pixabay","sha256":"hash"+str(i)} for i in range(5)]}
  self.reviews=[{"source_id":i,"provider":"pixabay","sha256":"hash"+str(i),"topic":"test TOP5","verified_by_human":True,"approved_for_render":True,"rights_reviewed":True,"rights_evidence_url":"https://example.org/license","license":"CC BY","rank_name":"검수완료","caption":"검수 완료된 실제 장면"} for i in range(5)]
 def test_no_approval_without_reviews(self):self.assertFalse(build(self.qa,{"reviews":[]})["approved"])
 def test_exact_fingerprint_pass(self):self.assertTrue(build(self.qa,{"reviews":self.reviews})["approved"])
 def test_hash_mismatch_blocks(self):
  self.reviews[0]["sha256"]="other"
  self.assertFalse(build(self.qa,{"reviews":self.reviews})["approved"])
 def test_missing_rights_blocks(self):
  self.reviews[0]["rights_reviewed"]=False
  self.assertFalse(build(self.qa,{"reviews":self.reviews})["approved"])
if __name__=="__main__":unittest.main()
