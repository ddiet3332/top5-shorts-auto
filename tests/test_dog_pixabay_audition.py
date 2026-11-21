import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_pixabay_audition import audition_pixabay, download_pixabay

class PixabayAuditionTests(unittest.TestCase):
    def test_preview_and_fail_closed_rights(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":[{"id":"PB-123","provider":"pixabay",
                "source_url":"https://pixabay.com/videos/dog-123/","creator":"A"}]}))
            def fake_download(video_id,key,path):
                self.assertEqual(video_id,123)
                path.write_bytes(b"sample")
                return {"duration_sec":8}
            def fake_preview(src,start,dst):
                dst.write_bytes(b"preview")
            result=audition_pixabay(discovery,root/"out","fake-key",downloader=fake_download,previewer=fake_preview)
            self.assertEqual(result["status"],"PREVIEW_READY")
            self.assertFalse(result["publication_approved"])
            self.assertEqual(result["candidates"][0]["rights_status"],"UNVERIFIED")
            self.assertFalse((root/"out"/"PB-123.mp4").exists())
            self.assertTrue((root/"out"/"PB-123_preview.mp4").exists())
    def test_rejects_untrusted_video_url(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                download_pixabay(123,"fake",Path(temp)/"file.mp4",fetch=lambda url:{"hits":[{
                    "id":123,"videos":{"medium":{"url":"https://evil.example/video.mp4"}}}]})
    def test_no_api_key_does_not_promote(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":[{"id":"PB-123","provider":"pixabay"}]}))
            result=audition_pixabay(discovery,root/"out","")
            self.assertEqual(result["status"],"NO_PREVIEW")
            self.assertFalse(result["publication_approved"])
if __name__=="__main__":
    unittest.main()
