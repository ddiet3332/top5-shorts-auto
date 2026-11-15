"""V19 public index remains tiny and cannot assert rights approval."""
import sys
import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from publish_v19_index import compact_index,publish_latest


class V19IndexTest(unittest.TestCase):
    def test_only_public_metadata_and_no_approval(self):
        audit={"candidates":[{
            "id":"PX-7680667","provider":"pexels","title":"Sphynx cat",
            "page_url":"https://www.pexels.com/video/a-sphynx-cat-jumping-on-a-stool-7680667/",
            "license_label":"Pexels License",
            "video_preview_status":"VIDEO_READY_FOR_HUMAN_REVIEW",
            "preview_windows":[{"preview_file":"V19_PEXELS/V12_PEXELS_PREVIEWS/PX-7680667_moment1.mp4"}],
            "asset_temporary_file":"/tmp/personal-secret-nope",
            "publication_approved":True}]}
        row=compact_index(audit,repo="ddiet3332/top5-shorts-auto",
                          run_id=123456,run_number=1,result="success")
        self.assertEqual(row["candidate_page_count"],1)
        self.assertEqual(row["preview_file_count"],1)
        self.assertFalse(row["publication_approved"])
        self.assertFalse(row["candidates"][0]["publication_approved"])
        self.assertNotIn("asset_temporary_file",json.dumps(row))
        with TemporaryDirectory() as tmp:
            self.assertTrue(publish_latest(row,Path(tmp)))
            self.assertTrue((Path(tmp)/"v19_latest.json").exists())

    def test_failed_job_cannot_claim_approval(self):
        row=compact_index(None,repo="a/b",run_id=2,run_number=2,result="failure")
        self.assertEqual(row["review_status"],"NO_VERIFIED_PREVIEW_RESULT")
        self.assertFalse(row["publication_approved"])

    def test_old_run_does_not_override_latest(self):
        with TemporaryDirectory() as tmp:
            new=compact_index(None,repo="a/b",run_id=45,run_number=45,result="failure")
            old=compact_index(None,repo="a/b",run_id=44,run_number=44,result="success")
            self.assertTrue(publish_latest(new,Path(tmp)))
            self.assertFalse(publish_latest(old,Path(tmp)))
            self.assertEqual(json.loads((Path(tmp)/"v19_latest.json").read_text())["run_id"],45)


if __name__=="__main__":
    unittest.main()
