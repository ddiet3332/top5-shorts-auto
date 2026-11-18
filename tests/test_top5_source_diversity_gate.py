import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_independent_review_qa import source_diversity_pass
class TestSourceDiversityGate(unittest.TestCase):
 def test_butterfly_old_run_rejected(self):
  self.assertFalse(source_diversity_pass(["kdv888","Kaffeesüchtig","KIMDAEJEUNG","Kaffeesüchtig","Kaffeesüchtig"]))
 def test_three_creators_pass(self):
  self.assertTrue(source_diversity_pass(["A","A","B","B","C"]))
 def test_unknown_creator_rejected(self):
  self.assertFalse(source_diversity_pass(["A","A","B","B",""]))
if __name__=="__main__":unittest.main()
