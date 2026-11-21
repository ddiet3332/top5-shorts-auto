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

    def test_provisionally_rejected_clip_is_skipped_for_rank_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovery=root/"discovery.json"
            rejection=root/"rejections.json"
            discovery.write_text(json.dumps({"candidates":[
                {"id":"PB-4740","provider":"pixabay","creator":"A"},
                {"id":"PB-987","provider":"pixabay","creator":"B"}]}))
            rejection.write_text(json.dumps({"schema_version":1,
                "scope":"rank5_rank2_replacement_only",
                "rejections":[{"id":"PB-4740"}]}))
            fetched=[]
            def fake_download(video_id,key,path,*,media_url):
                fetched.append(video_id)
                path.write_bytes(b"test media")
                return {"duration_sec":8}
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"0"}):
                result=audition_pixabay(discovery,root/"out","fake-key",
                    media_index={"PB-4740":"https://cdn.pixabay.com/4740.mp4",
                                 "PB-987":"https://cdn.pixabay.com/987.mp4"},
                    rejection_file=rejection,downloader=fake_download,
                    previewer=lambda _src,_start,target: target.write_bytes(b"preview"))
            self.assertEqual(fetched,[987])
            self.assertEqual(result["skipped_provisionally_rejected_ids"],["PB-4740"])
            self.assertEqual(result["status"],"PREVIEW_READY")
            self.assertFalse(result["publication_approved"])

    def test_cached_preview_survives_next_run_without_api_or_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovered=root/"candidates.json"
            discovered.write_text(json.dumps({"candidates":[
                {"id":"PB-998","provider":"pixabay","creator":"A"}]}))
            output=root/"audition"
            def get_video(video_id,key,path,*,media_url):
                path.write_bytes(b"original video")
                return {"duration_sec":12}
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"0"}):
                first=audition_pixabay(discovered,output,"fake-key",
                    media_index={"PB-998":"https://cdn.pixabay.com/video/998.mp4"},
                    downloader=get_video,
                    previewer=lambda src,start,dst:dst.write_bytes(b"preview data"))
            self.assertEqual(first["new_preview_count"],1)
            self.assertEqual(first["cached_preview_count"],0)
            self.assertEqual(first["candidates"][0]["preview_origin"],"NEW_THIS_RUN")
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"1"}):
                second=audition_pixabay(discovered,output,"fake-key",
                    media_index={},
                    downloader=lambda *args,**kwargs:self.fail("must not download cached video"))
            self.assertEqual(second["new_preview_count"],0)
            self.assertEqual(second["cached_preview_count"],1)
            self.assertEqual(second["candidates"][0]["id"],"PB-998")
            self.assertEqual(second["candidates"][0]["preview_origin"],"CACHED_PREVIOUS_RUN")
            self.assertFalse(second["publication_approved"])
            self.assertTrue((output/"PB-998_preview.mp4").exists())

    def test_cache_rotation_keeps_earlier_unreviewed_clip(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            discovered=root/"candidates.json"
            discovered.write_text(json.dumps({"candidates":[
                {"id":"PB-111","provider":"pixabay","creator":"A"},
                {"id":"PB-222","provider":"pixabay","creator":"B"}]}))
            output=root/"audition"
            saved=[]
            def download(video_id,key,path,*,media_url):
                saved.append(video_id)
                path.write_bytes(b"original")
                return {"duration_sec":12}
            previews=lambda src,start,target: target.write_bytes(b"preview")
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"0"}):
                first=audition_pixabay(discovered,output,"mock",max_items=1,
                    media_index={"PB-111":"https://cdn.pixabay.com/111.mp4"},
                    downloader=download,previewer=previews)
                second=audition_pixabay(discovered,output,"mock",max_items=1,
                    media_index={"PB-222":"https://cdn.pixabay.com/222.mp4"},
                    downloader=download,previewer=previews)
            self.assertEqual(saved,[111,222])
            self.assertEqual(second["new_preview_count"],1)
            self.assertEqual(second["cached_preview_count"],1)
            self.assertEqual({x["id"] for x in second["candidates"]},{"PB-111","PB-222"})
            self.assertFalse(second["publication_approved"])

    def test_rejected_cached_preview_is_not_carried_forward(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            output=root/"out"
            output.mkdir()
            (output/"PB-4740_preview.mp4").write_bytes(b"old")
            (output/"DOG_PIXABAY_AUDITION_RESULTS.json").write_text(json.dumps({
                "provider":"pixabay","candidates":[{"id":"PB-4740",
                "preview_file":"PB-4740_preview.mp4",
                "status":"PREVIEW_READY_REVIEW_REQUIRED"}]}))
            rejected=root/"rejections.json"
            rejected.write_text(json.dumps({"scope":"rank5_rank2_replacement_only",
                "schema_version":1,"rejections":[{"id":"PB-4740"}]}))
            discovery=root/"candidates.json"
            discovery.write_text(json.dumps({"candidates":[]}))
            result=audition_pixabay(discovery,output,"mock",
                media_index={},rejection_file=rejected)
            self.assertEqual(result["cached_preview_count"],0)
            self.assertEqual(result["status"],"NO_PREVIEW")
            self.assertFalse((output/"PB-4740_preview.mp4").exists())

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
