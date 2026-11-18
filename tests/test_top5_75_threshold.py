import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_independent_review_qa import MIN_EDITORIAL_SCORE,score_decision
class TestThreshold(unittest.TestCase):
 def test_threshold(self):
  self.assertEqual(MIN_EDITORIAL_SCORE,75)
  self.assertEqual(score_decision(74),"REVISE_BELOW_75")
  self.assertEqual(score_decision(75),"EDITORIAL_PASS_PUBLICATION_BLOCKED")
  self.assertEqual(score_decision(85),"EDITORIAL_PASS_PUBLICATION_BLOCKED")
  self.assertEqual(score_decision(None),"NOT_SCORED")
  self.assertEqual(score_decision(75,True,True),"EDITORIAL_PASS_REVIEW_FOR_PUBLICATION")
 def test_invalid(self):
  with self.assertRaises(ValueError):score_decision(101)
if __name__=="__main__":unittest.main()
