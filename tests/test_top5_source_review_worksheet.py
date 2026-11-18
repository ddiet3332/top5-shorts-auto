import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_source_review_worksheet import build
class WorksheetTests(unittest.TestCase):
 def test_never_auto_approves(self):
  data=build({"topic":"강아지의 웃긴 행동 TOP5","sources":[{"id":77509,"provider":"pixabay","sha256":"abc","file":"source_77509.mp4","page_url":"https://pixabay.com/videos/x","tags":"dog"}]})
  self.assertEqual(len(data["reviews"]),1)
  x=data["reviews"][0]
  self.assertEqual(x["sha256"],"abc")
  for key in ("scene_reviewed","scene_relevant","distinct_action","rights_reviewed","third_party_rights_cleared","likeness_rights_cleared","verified_by_human","approved_for_render"):
   self.assertIs(x[key],False)
if __name__=="__main__":unittest.main()
