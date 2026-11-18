import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_review_registry_bridge import build
class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.qa={"topic":"test TOP5","sources":[{"id":i,"provider":"pixabay","sha256":"hash"+str(i)} for i in range(5)]}
  self.reviews=[{"source_id":i,"provider":"pixabay","sha256":"hash"+str(i),"topic":"test TOP5","verified_by_human":True,"approved_for_render":True,"rights_reviewed":True,"scene_relevant":True,"scene_reviewed":True,"scene_description":"실제 웃긴 행동","distinct_action":True,"third_party_rights_cleared":True,"likeness_rights_cleared":True,"rights_evidence_url":"https://example.org/license","license":"CC BY","rank_name":"검수완료","caption":"검수 완료된 실제 장면"} for i in range(5)]
 def test_no_approval_without_reviews(self):self.assertFalse(build(self.qa,{"reviews":[]})["approved"])
 def test_exact_fingerprint_pass(self):self.assertTrue(build(self.qa,{"reviews":self.reviews})["approved"])
 def test_hash_mismatch_blocks(self):
  self.reviews[0]["sha256"]="other"
  self.assertFalse(build(self.qa,{"reviews":self.reviews})["approved"])
 def test_irrelevant_scene_blocks(self):
  self.reviews[0]["scene_relevant"]=False
  self.assertEqual(build(self.qa,{"reviews":self.reviews})["reason"],"SCENE_RELEVANCE_NOT_VERIFIED")
 def test_unresolved_likeness_blocks(self):
  self.reviews[0]["likeness_rights_cleared"]=False
  self.assertEqual(build(self.qa,{"reviews":self.reviews})["reason"],"THIRD_PARTY_OR_LIKENESS_RIGHTS_UNRESOLVED")
 def test_duplicate_action_blocks(self):
  self.reviews[0]["distinct_action"]=False
  self.assertEqual(build(self.qa,{"reviews":self.reviews})["reason"],"DISTINCT_TOP5_ACTION_NOT_VERIFIED")
 def test_missing_rights_blocks(self):
  self.reviews[0]["rights_reviewed"]=False
  self.assertFalse(build(self.qa,{"reviews":self.reviews})["approved"])
 def test_flight_requires_motion_evidence(self):
  self.qa["topic"]="잠자리의 비행 TOP5"
  for x in self.reviews:x["topic"]="잠자리의 비행 TOP5"
  self.assertEqual(build(self.qa,{"reviews":self.reviews})["reason"],"TOPIC_MOTION_NOT_VERIFIED")
  for x in self.reviews:x.update({"motion_reviewed":True,"motion_matches_topic":True})
  self.assertTrue(build(self.qa,{"reviews":self.reviews})["approved"])
  self.reviews[3]["motion_matches_topic"]=False
  self.assertEqual(build(self.qa,{"reviews":self.reviews})["source_id"],3)
if __name__=="__main__":unittest.main()
