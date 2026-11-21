import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_curated_pexels_audition import audition,load_catalog,resume


def source(video_id=31807439):
    return {
        "id":f"PX-{video_id}","provider":"pexels",
        "title":"Dog sliding across icy pond",
        "page_url":f"https://www.pexels.com/video/playful-dog-sliding-{video_id}/",
        "creator":"Filmmaker","license_label":"Pexels License",
        "license_url":"https://www.pexels.com/license/",
        "action_family_hypothesis":"ice_slide","rank_target":"rank5",
        "editorial_score":None,"reviewed_frames":False,"publication_approved":False,
    }


def catalog(root, *sources):
    path=root/"sources.json"
    path.write_text(json.dumps({"schema_version":1,
                                "sources":list(sources),
                                "publication_approved":False}),encoding="utf-8")
    return path


class CuratedPexelsTests(unittest.TestCase):
    def test_official_source_only_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            good=source()
            bad={**good,"page_url":"https://www.pexels.com.evil.test/video/dog-31807439/"}
            with self.assertRaises(ValueError):
                load_catalog(catalog(root,bad))
            bad={**good,"id":"PX-12345"}
            with self.assertRaises(ValueError):
                load_catalog(catalog(root,bad))
            bad={**good,"editorial_score":88}
            with self.assertRaises(ValueError):
                load_catalog(catalog(root,bad))
            self.assertEqual(load_catalog(catalog(root,good))[0]["id"],"PX-31807439")

    def test_three_actual_previews_and_resume_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sources=[source(i) for i in (31807439,5263686,10607242)]
            for i,row in enumerate(sources):
                row["action_family_hypothesis"]=("ice_slide","roll_studio","sledding_interaction")[i]
            p=catalog(root,*sources)
            out=root/"output"
            downloads=[]
            def downloader(item,path,max_bytes):
                self.assertLessEqual(max_bytes,125*1024*1024)
                downloads.append(item["id"])
                path.write_bytes(b"actual source data"*400)
                return {"duration_sec":9.0}
            def previewer(raw,start,dest):
                dest.write_bytes(b"preview"*400)
            def frames(raw,time,dest):
                dest.write_bytes(b"jpg")
            def windows(raw,duration,**kwargs):
                self.assertEqual(kwargs["seconds"],5.0)
                return [{"start":0.5,"motion":17.5}]
            report=audition(p,out,downloader=downloader,
                           previewer=previewer,window_picker=windows,
                           image_maker=frames)
            self.assertEqual(report["new_preview_count"],3)
            self.assertEqual(report["status"],"PREVIEW_READY")
            self.assertEqual(len(downloads),3)
            self.assertEqual(len(list(out.glob("*_preview.mp4"))),3)
            self.assertEqual(len(list(out.glob("*_frame*.jpg"))),9)
            self.assertFalse(list(out.glob("*_temporary.mp4")))
            self.assertFalse(report["publication_approved"])
            self.assertTrue(all(x["reviewed_frames"] is False and
                                x["editorial_score"] is None and
                                x["rights_status"]=="UNVERIFIED" for x in report["candidates"]))
            cached=resume(p,out)
            self.assertEqual(cached["new_preview_count"],0)
            self.assertEqual(cached["cached_preview_count"],3)
            self.assertTrue(all(x["preview_origin"]=="CACHED_PREVIOUS_RUN" for x in cached["candidates"]))
            self.assertFalse(cached["publication_approved"])

    def test_failed_download_leaves_no_preview_or_rights_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=catalog(root,source())
            out=root/"output"
            def fail(*args,**kwargs):
                raise RuntimeError("Official URL did not return a video file")
            result=audition(p,out,downloader=fail)
            self.assertEqual(result["status"],"NO_PREVIEW")
            self.assertEqual(result["candidates"][0]["status"],"AUDITION_FAILED")
            self.assertEqual(result["candidates"][0]["failure_code"],"NOT_A_VIDEO_RESPONSE")
            self.assertFalse(result["publication_approved"])


if __name__=="__main__":
    unittest.main()
