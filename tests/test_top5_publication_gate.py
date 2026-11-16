import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_publication_gate import evaluate,CATEGORIES

class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.qa={"editorial_scores":dict(CATEGORIES),
                 "full_video_review_evidence":{"reviewed":True,"reviewer":"human",
                     "reviewed_at":"2026-11-17","video_sha256":"a"*64}}
        self.rights={"source_rights_independently_cleared":True,
                     "all_five_sources_verified":True,
                     "youtube_reused_content_reviewed":True}
    def test_no_evidence_never_claims_80(self):
        self.qa.pop("full_video_review_evidence")
        self.assertFalse(evaluate(self.qa,self.rights)["report_80"])
    def test_metadata_proxy_not_accepted(self):
        self.qa["editorial_scores"]={"heuristic":100}
        self.assertIsNone(evaluate(self.qa,self.rights)["score"])
    def test_rights_fail_closed(self):
        self.rights["all_five_sources_verified"]=False
        r=evaluate(self.qa,self.rights)
        self.assertTrue(r["report_80"])
        self.assertFalse(r["publication_candidate_85"])
    def test_85_requires_both(self):
        r=evaluate(self.qa,self.rights)
        self.assertTrue(r["publication_candidate_85"])
        self.assertFalse(r["youtube_upload_permitted"])
    def test_low_score_not_reported(self):
        self.qa["editorial_scores"]["fun_reversal"]=0
        self.assertFalse(evaluate(self.qa,self.rights)["report_80"])
if __name__=="__main__":
    unittest.main()
