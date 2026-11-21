import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_rank5_hd_review import read_manifest, create_review, render_vertical


def spec():
    return {
        "schema_version":1,"review_only":True,"publication_approved":False,
        "id":"PX-5263686","provider":"pexels",
        "page_url":"https://www.pexels.com/video/cute-dog-rolling-on-his-back-5263686/",
        "creator":"KATRIN BOLOVTSOVA","license_label":"Pexels License",
        "license_url":"https://www.pexels.com/license/",
        "source_original_sha256_from_run_44879229566":"a"*64,
        "rank_target":"rank5","source_start_sec":2.0,
        "preview_duration_sec":5.0,"rights_status":"UNVERIFIED",
        "audio_approved":False,
    }


class DogRank5OriginalHDTests(unittest.TestCase):
    def test_original_video_render_contract_and_rights_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=root/"source.json";manifest.write_text(json.dumps(spec()))
            calls=[]
            def download(item,path,max_bytes):
                calls.append(("download",item["id"],max_bytes))
                path.write_bytes(b"source"*1000)
                return {"duration_sec":9.47}
            def render(src,target,*,start,seconds):
                calls.append(("render",start,seconds))
                target.write_bytes(b"rendered portrait"*1400)
            def verify(path):
                return {"width":1080,"height":1920,"fps":24,
                        "duration_sec":5.0,"full_decode":"PASS"}
            out=root/"review"
            result=create_review(manifest,out,downloader=download,
                                 renderer=render,verifier=verify)
            self.assertEqual(result["status"],"HD_REVIEW_READY")
            self.assertEqual(result["technical_review"]["height"],1920)
            self.assertTrue(result["render_from_original"])
            self.assertEqual(calls[1],("render",2.0,5.0))
            self.assertEqual(result["rights_status"],"UNVERIFIED")
            self.assertFalse(result["publication_approved"])
            self.assertFalse(result["source_audio_copied"])
            self.assertFalse((out/"_PX-5263686_temporary_original.mp4").exists())
            self.assertTrue((out/result["review_video_file"]).is_file())
            self.assertEqual(json.loads((out/"DOG_RANK5_HD_AUDITION.json").read_text())["status"],
                             "HD_REVIEW_READY")

    def test_source_crop_tracks_dog_right_in_late_frames(self):
        with patch("dog_rank5_hd_review.subprocess.run") as run:
            render_vertical(Path("source.mp4"),Path("review.mp4"),start=2.0,seconds=5.0)
            params=run.call_args.args[0]
            vf=params[params.index("-vf")+1]
            self.assertIn("tanh((t-3.2)*1.6)",vf)
            self.assertIn("crop=1080:1920",vf)
            self.assertIn("-an",params)
            self.assertIn("-t",params)
            self.assertEqual(params[params.index("-t")+1],"5.0")

    def test_rejects_arbitrary_page_and_preauthorization(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"bad.json"
            d=spec()
            for key,value in (("page_url","https://www.pexels.com.evil.test/video/fake-5263686/"),
                              ("publication_approved",True),
                              ("rights_status","CLEARED"),
                              ("audio_approved",True),
                              ("source_start_sec",-2.0)):
                altered={**d,key:value}
                p.write_text(json.dumps(altered))
                with self.subTest(key=key),self.assertRaises(ValueError):
                    read_manifest(p)

    def test_error_fails_closed_and_deletes_partial_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/"source.json";p.write_text(json.dumps(spec()))
            def bad(item,path,max_bytes):
                path.write_bytes(b"broken")
                raise RuntimeError("Official URL did not return a video file")
            out=root/"review"
            data=create_review(p,out,downloader=bad)
            self.assertEqual(data["status"],"HD_REVIEW_FAILED")
            self.assertEqual(data["failure_code"],"NOT_A_VIDEO_RESPONSE")
            self.assertFalse(data["publication_approved"])
            self.assertFalse(list(out.glob("*mp4")))


if __name__=="__main__":
    unittest.main()
