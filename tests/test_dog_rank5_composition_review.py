import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_rank5_composition_review import compose,validate_inputs,RANK5_ID


def report(video):
    return {
        "id":RANK5_ID,"rank":"rank5","status":"HD_REVIEW_READY",
        "render_from_original":True,
        "review_video_file":video.name,
        "source_original_sha256":"a"*64,
        "original_matches_prior_download":True,
        "source_audio_copied":False,
        "rights_status":"UNVERIFIED",
        "publication_approved":False,
        "technical_review":{"full_decode":"PASS"}
    }


def probe(path):
    duration=5 if "RANK5_ORIGINAL" in str(path) else 30
    frames=120 if duration==5 else 720
    return {"format":{"duration":duration},
            "streams":[{"codec_name":"h264","width":1080,
                        "height":1920,"nb_frames":frames}]}


class DogRank5ThirtySecondReviewTests(unittest.TestCase):
    def test_candidate_cannot_be_published_or_accepted_without_original_decode(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            base=root/"base.mp4";rank5=root/"PX-5263686_RANK5_ORIGINAL_PORTRAIT_REVIEW_1080x1920.mp4"
            for p in (base,rank5):p.write_bytes(b"media")
            meta=root/"rank5.json"
            data=report(rank5)
            with patch("dog_rank5_composition_review.probe_video",side_effect=probe):
                meta.write_text(json.dumps(data))
                self.assertEqual(validate_inputs(base,rank5,meta)["id"],RANK5_ID)
                for key,val in (("publication_approved",True),
                                ("rights_status","CLEARED"),
                                ("render_from_original",False),
                                ("source_audio_copied",True),
                                ("status","NOT_REVIEWED")):
                    changed={**data,key:val}
                    meta.write_text(json.dumps(changed))
                    with self.subTest(key=key),self.assertRaises(ValueError):
                        validate_inputs(base,rank5,meta)

    def test_composite_is_separate_review_with_unmodified_aac(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            base=root/"base.mp4";rank5=root/"PX-5263686_RANK5_ORIGINAL_PORTRAIT_REVIEW_1080x1920.mp4"
            for p in (base,rank5):p.write_bytes(b"media")
            meta=root/"rank5.json";meta.write_text(json.dumps(report(rank5)))
            out=root/"out"
            font=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
            self.assertTrue(font.is_file())
            calls=[]
            def fake_ffmpeg(args,**kwargs):
                calls.append(args)
                Path(args[-1]).write_bytes(b"review"*6000)
            with (patch("dog_rank5_composition_review.probe_video",side_effect=probe),
                  patch("dog_rank5_composition_review.audio_bitstream_sha",return_value="a"*64),
                  patch("dog_rank5_composition_review.subprocess.run")):
                result=compose(base,rank5,meta,out,ffmpeg=fake_ffmpeg,fontfile=font)
            self.assertEqual(len(calls),2)
            self.assertIn("enable='gte(t,2)*lt(t,7)'"," ".join(calls[1]))
            self.assertIn("-c:a"," ".join(calls[1]))
            self.assertIn("copy"," ".join(calls[1]))
            self.assertEqual(result["status"],"EDITORIAL_REVIEW_READY_NOT_FOR_PUBLICATION")
            self.assertEqual(result["replaced_frame_range"],[48,167])
            self.assertFalse(result["publication_approved"])
            self.assertEqual(result["right_to_use_video"],"UNVERIFIED")
            self.assertTrue((out/result["video_file"]).is_file())
            self.assertFalse((out/"_rank5_setup.png").exists())
            self.assertFalse((out/"_rank5_segment.mp4").exists())


if __name__=="__main__":
    unittest.main()
