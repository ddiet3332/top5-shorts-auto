"""Human stock fallback proves five distinct real sources or stays BLOCKED."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_universal_stock_fallback import (FALLBACK_VIDEO, EXPORT_VIDEO,
    human_plan, assess_human_fallback, run_human_fallback, save)


def stream_info(_):
    return {"format": {"duration": "30.0"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080,
                 "height": 1920, "r_frame_rate": "24/1", "nb_frames": "720"},
                {"codec_type": "audio", "codec_name": "aac"}]}


class HumanStockFallbackTests(unittest.TestCase):
    def make_sources_and_video(self, out):
        sources=out/"stock_fallback/sources"
        render=out/"stock_fallback/render"
        sources.mkdir(parents=True)
        render.mkdir(parents=True)
        video=render/FALLBACK_VIDEO
        video.write_bytes(b"mocked 30s h264 video (no actual media)")
        rows=[{"provider":"pixabay", "id": i, "creator":f"owner-{i}",
               "page_url":f"https://pixabay.com/videos/id-{i}/",
               "sha256":hashlib.sha256(f"source-{i}".encode()).hexdigest(),
               "full_video_decode":True, "rights_verified":False}
              for i in range(5)]
        save(sources/"SOURCE_DOWNLOAD_QA.json",
             {"topic":"놀라운 댄스 동작 TOP5", "sources":rows,"topic_attempts":[]})
        save(render/"GENERIC_V06_QA.json",
             {"file":FALLBACK_VIDEO,
              "sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
              "technical_checks":{"format":True,"audio":True,"full_decode":True,
                                  "black":True,"hook_motion":True},
              "editorial_score":None,"rights_verified":False,
              "publication_approved":False})
        return sources,render

    def test_human_topics_are_neither_dogs_nor_unrelated_filler(self):
        p=human_plan()
        all_=[p["selected"],*p["alternatives"]]
        self.assertEqual(len(all_),3)
        self.assertTrue(all(x["category"]=="people" for x in all_))
        self.assertTrue(all(x["search_queries"] for x in all_))
        self.assertFalse(p["publication_approved"])

    def test_technical_pass_still_blocks_ypp_and_exports_actual_working_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.make_sources_and_video(root)
            result=assess_human_fallback(root,probe=stream_info)
            self.assertTrue(result["technical_pass"])
            self.assertEqual(result["status"],"TECHNICAL_PASS_STOCK_FALLBACK_REVIEW_ONLY")
            self.assertTrue((root/EXPORT_VIDEO).is_file())
            self.assertIsNone(result["final_editorial_score_100"])
            self.assertFalse(result["publication_approved"])
            self.assertFalse(result["rights_verified"])

    def test_source_duplicates_or_forged_rights_cannot_be_passed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source,render=self.make_sources_and_video(root)
            manifest=json.loads((source/"SOURCE_DOWNLOAD_QA.json").read_text())
            manifest["sources"][4]["sha256"]=manifest["sources"][0]["sha256"]
            save(source/"SOURCE_DOWNLOAD_QA.json",manifest)
            result=assess_human_fallback(root,probe=stream_info)
            self.assertFalse(result["technical_pass"])
            self.assertFalse((root/EXPORT_VIDEO).exists())

            manifest["sources"][4]["sha256"]=hashlib.sha256(b"new source").hexdigest()
            save(source/"SOURCE_DOWNLOAD_QA.json",manifest)
            qa=json.loads((render/"GENERIC_V06_QA.json").read_text())
            qa["publication_approved"]=True
            save(render/"GENERIC_V06_QA.json",qa)
            self.assertFalse(assess_human_fallback(root,probe=stream_info)["technical_pass"])

    def test_actual_pixabay_flamingos_dancing_are_not_a_human_dance_clip(self):
        from top5_free_source_download import obvious_topic_mismatch
        topic="놀라운 댄스 동작 TOP5"
        self.assertTrue(obvious_topic_mismatch(
            "flamingo, flamingos, birds, dancing, animals, pink, pond",topic))
        self.assertTrue(obvious_topic_mismatch(
            "puppy, dog, dancing, animals",topic))
        self.assertFalse(obvious_topic_mismatch(
            "girl, ballerina, dancing, dance, festival",topic))
        self.assertFalse(obvious_topic_mismatch(
            "couple, dancers, silhouette, dance off, street dancer",topic))

        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source,_=self.make_sources_and_video(root)
            manifest=json.loads((source/"SOURCE_DOWNLOAD_QA.json").read_text())
            manifest["sources"][4]["tags"]="flamingo, flamingos, birds, dancing, animals"
            save(source/"SOURCE_DOWNLOAD_QA.json",manifest)
            result=assess_human_fallback(root,probe=stream_info)
            self.assertFalse(result["technical_pass"])
            self.assertFalse(result["publication_approved"])
            self.assertFalse((root/EXPORT_VIDEO).exists())

    def test_reviewed_rejected_human_source_ids_are_excluded_before_download(self):
        from top5_free_source_download import inspect
        registry=json.loads((Path(__file__).resolve().parents[1]/
                             "review/rejected_source_ids.json").read_text())
        bad=set(registry["놀라운 댄스 동작 TOP5"])
        self.assertEqual(bad,{76124,15922})
        hits=[
            {"id":ident,"tags":"dance, dancing, ballerina, person",
             "user":f"creator-{ident}","duration":10.0,
             "pageURL":f"https://pixabay.com/videos/id-{ident}/",
             "videos":{"medium":{"url":f"https://cdn.example/{ident}.mp4"}}}
            for ident in [76124,15922,111,112,113,114,115,116]]
        fetched=[]
        def fake_download(url,path,max_bytes=None):
            fetched.append(url)
            Path(path).write_bytes(url.encode())
        with tempfile.TemporaryDirectory() as td:
            with (patch("top5_free_source_download.download",side_effect=fake_download),
                  patch("top5_free_source_download.probe",return_value=9.0),
                  patch("top5_free_source_download.decode")):
                result=inspect("dummy",{
                    "selected":{"topic":"놀라운 댄스 동작 TOP5","category":"people",
                                "search_queries":["dance","dancing"]}},
                    Path(td),fetch=lambda key,query:hits,rejected=bad)
        self.assertEqual(result["downloaded_valid_sources"],5)
        self.assertTrue(all(row["id"] not in bad for row in result["sources"]))
        self.assertTrue(all("76124" not in url and "15922" not in url for url in fetched))

    def test_no_key_is_a_clear_source_blocker_not_a_fake_video(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ,{"PIXABAY_API_KEY":""}):
                result=run_human_fallback(Path(td))
            self.assertEqual(result["status"],"BLOCKED_PIXABAY_KEY_UNAVAILABLE")
            self.assertFalse(result["technical_pass"])
            self.assertFalse(result["publication_approved"])


if __name__ == "__main__":
    unittest.main()
