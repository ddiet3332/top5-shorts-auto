import hashlib
import tempfile
import unittest
from pathlib import Path
from src.top5_quality_gate import assess_quality

class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.video=Path(self.tmp.name)/"video.mp4"
        self.video.write_bytes(b"fake video bytes for deterministic hash test")
        self.card={"full_av_review_complete":True,
                   "reviewed_video_sha256":hashlib.sha256(self.video.read_bytes()).hexdigest(),
                   "dimensions":{"hook":18,"humor_payoff":22,"ranking":13,"flow":13,
                                 "creative_captions":9,"sound":8}}
    def tearDown(self): self.tmp.cleanup()
    def test_83_pass_with_rights_deferred(self):
        r=assess_quality(self.card,{"technical_pass":True},self.video)
        self.assertEqual(r["quality_score_100"],83)
        self.assertTrue(r["quality_80_pass"])
        self.assertFalse(r["youtube_auto_upload"])
    def test_missing_av_evidence_fails(self):
        self.card["full_av_review_complete"]=False
        self.assertIsNone(assess_quality(self.card,{"technical_pass":True},self.video)["quality_score_100"])
    def test_hash_mismatch_fails(self):
        self.card["reviewed_video_sha256"]="0"*64
        self.assertFalse(assess_quality(self.card,{"technical_pass":True},self.video)["quality_80_pass"])
    def test_technical_failure_fails(self):
        self.assertFalse(assess_quality(self.card,{"technical_pass":False},self.video)["quality_80_pass"])
if __name__=="__main__":unittest.main()
