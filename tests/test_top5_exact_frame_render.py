"""Detect real near-EOF stock cuts that used to lose a frame and fail /720 gate."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import top5_production_review as review


class ExactFrameRenderTests(unittest.TestCase):
    def test_renderer_forces_six_seconds_as_144_exact_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with (patch.object(review, "overlay"), patch.object(review, "run") as run):
                listing=review.render_parts(
                    root, "사람들의 춤", root,
                    [{"file": "sample.mp4", "cut_start_sec": 12.987}],
                    ["장면 내용 검수 필요"], "ultrafast")
            self.assertTrue(listing.exists())
            self.assertEqual(run.call_count,1)
            cmd=run.call_args.args[0]
            self.assertEqual(cmd[cmd.index("-frames:v")+1],"144")
            self.assertEqual(cmd[cmd.index("-fps_mode")+1],"cfr")
            self.assertEqual(cmd[cmd.index("-r")+1],"24")
            filt=cmd[cmd.index("-filter_complex")+1]
            for required in (
                "tpad=stop_mode=clone:stop_duration=1",
                "trim=end_frame=144", "setpts=N/(24*TB)"):
                self.assertIn(required,filt)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg unavailable")
    def test_actual_near_eof_cut_and_five_cut_concat_are_720_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/"source.mp4"
            part=root/"rank.mp4"
            listfile=root/"list.txt"
            audio=root/"sound.wav"
            final=root/"result.mp4"
            def run(*args):
                subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-y",*args],
                               check=True,timeout=90)
            def probe(path):
                return json.loads(subprocess.check_output([
                    "ffprobe","-v","error","-show_streams","-show_format",
                    "-of","json",str(path)],timeout=20))
            run("-f","lavfi","-i","testsrc2=size=160x288:rate=30000/1001:duration=6.00",
                "-an","-c:v","libx264","-preset","ultrafast",str(source))
            # Last ~40ms unavailable: padding holds last genuine frame.
            run("-ss","0.042","-i",str(source),"-vf",
                "fps=24,tpad=stop_mode=clone:stop_duration=1,"
                "trim=end_frame=144,setpts=N/(24*TB),format=yuv420p",
                "-frames:v","144","-fps_mode","cfr","-r","24",
                "-an","-c:v","libx264","-preset","ultrafast",str(part))
            v=next(s for s in probe(part)["streams"] if s["codec_type"]=="video")
            self.assertEqual((v["nb_frames"],v["r_frame_rate"],float(v["duration"])),
                             (str(144),"24/1",6.0))
            listfile.write_text("".join("file 'rank.mp4'\n" for _ in range(5)))
            run("-f","lavfi","-i","sine=frequency=440:duration=30",
                "-c:a","pcm_s16le",str(audio))
            run("-f","concat","-i",str(listfile),"-i",str(audio),
                "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
                "-b:a","160k","-movflags","+faststart",str(final))
            info=probe(final)
            streams=info["streams"]
            vid=next(s for s in streams if s["codec_type"]=="video")
            aud=next(s for s in streams if s["codec_type"]=="audio")
            self.assertEqual(vid["nb_frames"],"720")
            self.assertEqual(vid["r_frame_rate"],"24/1")
            self.assertAlmostEqual(float(vid["duration"]),30,places=2)
            self.assertAlmostEqual(float(aud["duration"]),30,places=2)
            subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(final),
                            "-map","0:v:0","-map","0:a:0","-f","null","-"],
                           check=True,timeout=80)


if __name__=="__main__":
    unittest.main()
