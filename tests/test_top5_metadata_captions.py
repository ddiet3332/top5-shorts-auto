import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_generic_v06_preview import source_label
class TestMetadataCaptions(unittest.TestCase):
 def test_known_tags(self):
  self.assertEqual(source_label({"tags":"butterfly, flower, macro"}),"꽃 · 접사")
 def test_no_visual_claims(self):
  self.assertEqual(source_label({"tags":"butterfly, insect"}),"나비 영상")
 def test_dedup(self):
  self.assertEqual(source_label({"tags":"flower, blossom, macro"}),"꽃 · 접사")
if __name__=="__main__":unittest.main()
