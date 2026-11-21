import json
import os
import sys
import tempfile
import urllib.error
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
    def test_transient_media_index_skips_second_pixabay_api_query(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":[{"id":"PB-123","provider":"pixabay",
                "source_url":"https://pixabay.com/videos/id-123/","creator":"A"}]}))
            seen=[]
            def direct_download(video_id,key,path,*,media_url):
                seen.append(media_url)
                path.write_bytes(b"original video data")
                return {"duration_sec":8}
            def previewer(_src,_start,target):
                target.write_bytes(b"preview data")
            result=audition_pixabay(discovery,root/"out","fake-key",
                media_index={"PB-123":"https://cdn.pixabay.com/video/123.mp4"},
                downloader=direct_download,previewer=previewer)
            self.assertEqual(result["status"],"PREVIEW_READY")
            self.assertEqual(seen,["https://cdn.pixabay.com/video/123.mp4"])
            self.assertNotIn("cdn.pixabay.com",str(result))
            self.assertFalse(result["publication_approved"])

    def test_http_failure_status_is_preserved_without_url(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":[{"id":"PB-123","provider":"pixabay"}]}))
            def reject(video_id,key,path,*,media_url):
                raise urllib.error.HTTPError("https://cdn.pixabay.com/video/123.mp4",403,
                                             "Forbidden",{},None)
            result=audition_pixabay(discovery,root/"out","fake-key",
                media_index={"PB-123":"https://cdn.pixabay.com/video/123.mp4"},
                downloader=reject)
            self.assertEqual(result["status"],"NO_PREVIEW")
            self.assertEqual(result["candidates"][0]["http_status"],403)
            self.assertFalse(result["publication_approved"])
            self.assertNotIn("cdn.pixabay.com",str(result))

    def test_direct_media_url_rejects_untrusted_host_without_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,"UNTRUSTED_VIDEO_HOST"):
                download_pixabay(123,"fake",Path(temp)/"video.mp4",
                    media_url="https://evil.example/video.mp4",
                    fetch=lambda _:self.fail("must not perform API lookup"))

    def test_four_daily_previews_use_distinct_creators_before_repeats(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            rows=[{"id":"PB-"+str(i),"provider":"pixabay","creator":creator}
                  for i,creator in ((1,"A"),(2,"A"),(3,"B"),(4,"C"),(5,"D"))]
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":rows}))
            picked=[]
            def download(video_id,key,path,*,media_url):
                picked.append(video_id)
                path.write_bytes(b"video")
                return {"duration_sec":8}
            def preview(_src,_start,dst):
                dst.write_bytes(b"preview")
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"0"}):
                result=audition_pixabay(discovery,root/"out","mock",
                   media_index={"PB-"+str(i):"https://cdn.pixabay.com/video/"+str(i)+".mp4"
                                for i in range(1,6)},
                   downloader=download,previewer=preview)
            self.assertEqual(picked,[1,3,4,5])
            self.assertEqual(result["status"],"PREVIEW_READY")
            self.assertEqual(len(result["candidates"]),4)
            self.assertFalse(result["publication_approved"])

    def test_rejects_untrusted_video_url(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                download_pixabay(123,"fake",Path(temp)/"file.mp4",fetch=lambda url:{"hits":[{
                    "id":123,"videos":{"medium":{"url":"https://evil.example/video.mp4"}}}]})
    def test_rejects_non_video_content_type(self):
        from unittest.mock import Mock
        class FakeResponse:
            headers={"Content-Type":"text/html"}
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return "https://cdn.pixabay.com/video.mp4"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,"NOT_VIDEO_RESPONSE"):
                download_pixabay(123,"fake",Path(temp)/"file.mp4",
                    fetch=lambda url:{"hits":[{"id":123,"videos":{"medium":{"url":"https://cdn.pixabay.com/video.mp4"}}}]},
                    opener=lambda request,timeout:FakeResponse())
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
