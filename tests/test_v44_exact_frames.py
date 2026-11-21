"""Regression for real run #44917082072 (objects: 717 video frames/30s AAC)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from v28_fullscreen_builder import create_scene
from top5_auto_v29 import technical_qa

def frames(path):
    p=subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=nb_frames,duration,r_frame_rate",
        "-of","json",str(path)],text=True,timeout=30)
    return json.loads(p)["streams"][0]

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg+ffprobe required")
class RealSceneEOFTests(unittest.TestCase):
    def _source(self,folder,duration):
        src=folder/"source.mp4"
        subprocess.run([
            "ffmpeg","-v","error","-nostdin","-y",
            "-f","lavfi","-i",f"testsrc2=size=160x288:rate=24:duration={duration}",
            "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(src)
        ],check=True,timeout=30)
        return src

    def test_last_three_input_frames_missing_but_output_exact_24(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            source=self._source(root,1.0)
            destination=root/"scene.mp4"
            create_scene(source,0.125,1,destination)
            info=frames(destination)
            self.assertEqual(info["nb_frames"],"24")
            self.assertEqual(info["r_frame_rate"],"24/1")
            self.assertAlmostEqual(float(info["duration"]),1.0,places=2)

    def test_missing_more_than_0_2_seconds_fails_instead_of_faking_motion(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            source=self._source(root,0.4)
            destination=root/"short.mp4"
            with self.assertRaises(ValueError):
                create_scene(source,0,1,destination)

class FinalTechnicalGateTests(unittest.TestCase):
    def _fake_evidence(self,n):
        return json.dumps({"streams":[
            {"codec_type":"video","codec_name":"h264",
             "width":1080,"height":1920,"r_frame_rate":"24/1",
             "nb_frames":str(n),"duration":str(n/24)},
            {"codec_type":"audio","codec_name":"aac","duration":"30.00"}
        ],"format":{"duration":"30.00"}}).encode()

    def test_717_frames_not_reported_as_technical_success(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with patch("top5_auto_v29.subprocess.check_output",return_value=self._fake_evidence(717)):
                with self.assertRaises(RuntimeError):
                    technical_qa(p/"fake.mp4",p,{"topic_id":"objects_oddities"},[{}]*5)

    def test_full_720_count_still_subject_to_decode_and_frames_review(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with patch("top5_auto_v29.subprocess.check_output",return_value=self._fake_evidence(720)), \
                 patch("top5_auto_v29.run",side_effect=RuntimeError("decode fails")):
                with self.assertRaisesRegex(RuntimeError,"decode fails"):
                    technical_qa(p/"fake.mp4",p,{"topic_id":"objects_oddities"},[{}]*5)

if __name__=="__main__":
    unittest.main()
