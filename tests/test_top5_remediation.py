import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_remediation import plan
class RemediationTests(unittest.TestCase):
    def setUp(self):
        self.clips=[dict(rank=i,source_page=f"original-{i}",verified=True,
                         editorial_score=80,minimum_score=70) for i in range(1,6)]
        self.clips[0]["editorial_score"]=40
        self.options=[dict(source_page="replacement-1",editorial_reviewed=True,
                           rights_independently_cleared=True,creator="creator",
                           license_evidence_url="https://example.org/license",editorial_score=90)]
    def test_replace_only_with_cleared_better_source(self):
        r=plan({"clips":self.clips},self.options)
        self.assertEqual(r["status"],"READY_FOR_REBUILD")
        self.assertFalse(r["publication_approved"])
    def test_rights_unknown_blocks(self):
        self.options[0]["rights_independently_cleared"]=False
        self.assertEqual(plan({"clips":self.clips},self.options)["status"],"BLOCKED")
    def test_unreviewed_clip_blocks(self):
        self.clips[2]["verified"]=False
        self.assertEqual(plan({"clips":self.clips},self.options)["reason"],"unreviewed_clips")
    def test_three_repair_limit(self):
        self.assertEqual(plan({"clips":self.clips},self.options,3)["status"],"STOP")
    def test_replacement_must_be_strictly_better(self):
        self.options[0]["editorial_score"]=39
        self.assertEqual(plan({"clips":self.clips},self.options)["status"],"BLOCKED")
    def test_no_weak_clips(self):
        self.clips[0]["editorial_score"]=80
        self.assertEqual(plan({"clips":self.clips},self.options)["status"],"NO_CHANGE")
if __name__=="__main__":
    unittest.main()
