"""Pre-render objective source-window visibility and location diversity regression."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_candidate_visual_gate import (
    FRAME_BYTES, raw_grayscale_luminance, inspect_original_window,
    named_nature_site, diverse_scene_selection)
from top5_auto_v30 import select_sources
from top5_hook_selection import SourceShortage


class CandidateVisualGateTests(unittest.TestCase):
    def test_cropped_real_grayscale_detects_sustained_darkness_not_bright_border(self):
        # Center of frame is dark, even if the surround contains brilliant
        # UI/bar pixels. This matches footage rather than design chrome.
        def make_frame(center):
            rows = []
            for y in range(96):
                for x in range(64):
                    rows.append(center if 12 <= y < 84 and 8 <= x < 56 else 245)
            return bytes(rows)
        self.assertEqual(len(make_frame(0)), FRAME_BYTES)
        data = make_frame(0) * 5 + make_frame(90)
        metrics = raw_grayscale_luminance(data)
        self.assertEqual(metrics["sample_count"], 6)
        self.assertEqual(metrics["near_dark_count"], 5)
        self.assertTrue(metrics["mostly_dark"])
        self.assertIsNone(metrics["editorial_score"])
        self.assertFalse(metrics["semantic_action_verified"])
        bright = raw_grayscale_luminance(make_frame(90) * 6)
        self.assertFalse(bright["mostly_dark"])
        with self.assertRaises(ValueError):
            raw_grayscale_luminance(b"invalid")
        with self.assertRaises(ValueError):
            raw_grayscale_luminance(make_frame(0) * 2)

    def test_named_landmark_diversity_is_exact_and_conservative(self):
        titles = [
            "File:Video from behind Kawaida Waterfall through hanging roots.webm",
            "File:Side view video of Kawaida Waterfall cascading.webm",
            "File:MT Slamet Volcano eruption.webm",
            "File:Tonga Volcano Eruption visible.webm",
            "File:Lightning Storm in Rolla.webm",
            "File:Wave at Bondi Beach.webm"]
        self.assertEqual(named_nature_site(titles[0]), "waterfall:kawaida")
        self.assertEqual(named_nature_site(titles[1]), "waterfall:kawaida")
        self.assertEqual(named_nature_site(titles[2]), "volcano:slamet")
        self.assertEqual(named_nature_site(titles[3]), "volcano:tonga")
        self.assertIsNone(named_nature_site(titles[4]))
        self.assertIsNone(named_nature_site("File:Waterfall in the rain.webm"))
        chosen,dupes=diverse_scene_selection([{"title":t} for t in titles])
        self.assertEqual(len(chosen),5)
        self.assertEqual(len(dupes),1)
        self.assertEqual(dupes[0]["site_key"],"waterfall:kawaida")

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg not installed")
    def test_actual_generated_short_dark_and_bright_video_windows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for level,want_dark in ((0,True),(150,False)):
                path=root/f"{level}.mp4"
                subprocess.run([
                    "ffmpeg","-nostdin","-v","error","-y","-f","lavfi",
                    "-i",f"color=c=0x{level:02x}{level:02x}{level:02x}:s=160x240:r=24:d=7",
                    "-c:v","libx264","-preset","ultrafast",str(path)
                ],check=True,timeout=40)
                v=inspect_original_window(path,0.2)
                self.assertGreaterEqual(v["sample_count"],5)
                self.assertEqual(v["mostly_dark"],want_dark)

    def _source(self,title,i):
        return {"title":title,"source_page":f"https://commons.wikimedia.org/wiki/{i}",
                "author":f"creator{i}","license":"CC BY",
                "license_url":"https://creativecommons.org/licenses/by/4.0/",
                "title_score":8.0,"discovery_rank":12.0}

    def test_source_selection_rejects_dark_window_before_render_and_uses_unique_sites(self):
        originals=[
            "File:Kawaida Waterfall from behind.webm",
            "File:Side view video of Kawaida Waterfall cascading.webm",
            "File:MT Slamet Volcano eruption.webm",
            "File:Tonga Volcano Eruption.webm",
            "File:Kansas Tornado Approaching.webm",
            "File:Yellowstone Geyser Eruption.webm",
            "File:Alps Glacier Cracking.webm"]
        candidates=[self._source(t,i) for i,t in enumerate(originals)]
        def download(src,path):
            Path(path).write_bytes(src["title"].encode())
        def brightness(path,start):
            if "Slamet" in str(Path(path).read_bytes()):
                return {"mostly_dark":True,"near_dark_count":6}
            return {"mostly_dark":False,"near_dark_count":0}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with (patch("top5_auto_v30.download_video",side_effect=download),
                  patch("top5_auto_v30.probe_duration",return_value=14.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(2.0,12.0)),
                  patch("top5_auto_v30.checked_scenes",return_value={}),
                  patch("top5_auto_v30.inspect_original_window",side_effect=brightness),
                  patch("top5_auto_v30.reviewed_weak_window",return_value=None)):
                chosen,attempts=select_sources(candidates,root,
                    topic={"topic_id":"nature_moments","category":"자연"})
            self.assertEqual(len(chosen),5)
            self.assertEqual(sum("Slamet" in t["title"] for t in chosen),0)
            self.assertEqual(sum("Kawaida" in t["title"] for t in chosen),1)
            self.assertTrue(any(t["status"]=="REJECTED" and
                "SOURCE_WINDOW_MOSTLY_DARK" in t["why"] for t in attempts))
            evidence=json.loads((root/"V30_SOURCE_SCENE_DIVERSITY.json").read_text())
            self.assertGreaterEqual(len(evidence["duplicate_site_candidates"]),1)
            self.assertFalse(evidence["publication_approved"])

    def test_no_five_distinct_landmarks_refuses_to_fill_rank_with_duplicate(self):
        names=[
            "File:Kawaida Waterfall front.webm",
            "File:Kawaida Waterfall back.webm",
            "File:Kawaida Waterfall side.webm",
            "File:Tonga Volcano Eruption.webm",
            "File:Mt Slamet Volcano Eruption.webm"]
        candidates=[self._source(t,i) for i,t in enumerate(names)]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with (patch("top5_auto_v30.download_video",
                        side_effect=lambda src,path:Path(path).write_bytes(src["title"].encode())),
                  patch("top5_auto_v30.probe_duration",return_value=14.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(2.0,8.0)),
                  patch("top5_auto_v30.checked_scenes",return_value={}),
                  patch("top5_auto_v30.inspect_original_window",
                        return_value={"mostly_dark":False,"near_dark_count":0}),
                  patch("top5_auto_v30.reviewed_weak_window",return_value=None)):
                with self.assertRaises(SourceShortage):
                    select_sources(candidates,root,
                                   topic={"topic_id":"nature_moments","category":"자연"})
            report=json.loads((root/"V30_SOURCE_SCENE_DIVERSITY.json").read_text())
            self.assertEqual(report["distinct_named_site_count"],3)
            self.assertEqual(len(report["duplicate_site_candidates"]),2)


if __name__=="__main__":
    unittest.main()
