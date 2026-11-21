"""The storyboard must be about real ranked video cuts, never unverified scoring."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_scene_evidence import (
    VIDEO,V32_WINDOWS,evaluate_video,validate_plan,sample_times,possible_repeated_subject)


def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf-8")


class RankEvidenceTests(unittest.TestCase):
    def fixtures(self,folder):
        root=Path(folder)
        video=root/VIDEO
        video.write_bytes(b"real_MP4_mock_for_wiring_tests")
        sha=hashlib.sha256(video.read_bytes()).hexdigest()
        save(root/"UNIVERSAL_TOPIC_TRIAL.json",{
            "requested_topic":"nature_moments","technical_pass":True,
            "publication_approved":False,"video_sha256":sha})
        titles=[
            "File:Kawaida Waterfall Side View.webm",
            "File:Lightning Clouds Over America.webm",
            "File:Kawaida Waterfall Rear View.webm",
            "File:Tonga Volcano Eruption Satellite.webm",
            "File:Rolla Night Lightning Storm.webm"]
        save(root/"SELECTED_SOURCE_PROVENANCE.json",{
            "selected":[{"rank":rank,"sha256":hashlib.sha256(f"source{i}".encode()).hexdigest(),
                          "source_page":f"https://commons.wikimedia.org/{i}"}
                         for i,(rank,a,b) in enumerate(V32_WINDOWS)]})
        save(root/"SOURCE_SELECTION_REVIEW.json",{
            "items_in_rank_5_to_1_order":[{"title":t} for t in titles]})
        return root

    def test_full_35_frame_actual_ranks_include_warnings_not_fake_editorial_score(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.fixtures(td)
            def fake_frame(video,second):
                # A dark 1st-place rank, visible other scenes. A high-contrast
                # silhouette would receive a warning, not an automatic fail.
                return Image.new("RGB",(360,640),
                                 (0,0,0) if 21 <= second < 27 else (130,130,130))
            report=evaluate_video("nature_moments",root,capture_frame=fake_frame)
            self.assertEqual(report["status"],"SCENE_EVIDENCE_REVIEW_REQUIRED")
            self.assertEqual(report["rank_count"],5)
            self.assertEqual(sum(len(r["samples"]) for r in report["ranks"]),35)
            self.assertEqual(report["ranks"][-1]["near_dark_sample_count"],7)
            self.assertIn("DARK_OR_HIGH_CONTRAST_CONTENT_REVIEW",
                          report["ranks"][-1]["review_flags"])
            self.assertIn("PLACEHOLDER_CAPTION_NOT_PUBLISHABLE",
                          report["ranks"][0]["review_flags"])
            self.assertTrue(report["repeated_title_cues"])
            self.assertFalse(report["publication_approved"])
            self.assertIsNone(report["editorial_score_100"])
            self.assertTrue((root/"TOP5_ACTUAL_35FRAME_STORYBOARD.jpg").is_file())
            self.assertTrue((root/"TOP5_SCENE_EVIDENCE.json").is_file())
            self.assertTrue((root/"TOP5_SCENE_REVIEW_CHECKLIST.md").is_file())

    def test_video_hash_mismatch_cannot_receive_scene_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.fixtures(td)
            p=root/"UNIVERSAL_TOPIC_TRIAL.json"
            row=json.loads(p.read_text())
            row["video_sha256"]="bad"
            save(p,row)
            with self.assertRaisesRegex(ValueError,"ACTUAL_VIDEO_NOT_MATCHING"):
                evaluate_video("nature_moments",root,
                               capture_frame=lambda *a:Image.new("RGB",(360,640)))

    def test_window_integrity_prevents_mixing_footage(self):
        good=[{"rank":rank,"start":a,"end":b,
               "source_sha256":hashlib.sha256(f"clip{i}".encode()).hexdigest(),
               "source_url":f"https://commons.wikimedia.org/{i}",
               "original_title":f"File:{i}.webm"}
              for i,(rank,a,b) in enumerate(V32_WINDOWS)]
        validate_plan(good)
        bad=[dict(x) for x in good]
        bad[1]["source_sha256"]=bad[0]["source_sha256"]
        with self.assertRaisesRegex(ValueError,"RANK_SOURCE"):
            validate_plan(bad)
        bad=[dict(x) for x in good]
        bad[1]["start"]=9.2
        with self.assertRaisesRegex(ValueError,"NOT_CONTIGUOUS"):
            validate_plan(bad)
        self.assertEqual(len(sample_times(21.,27.)),7)
        self.assertGreater(sample_times(21.,27.)[0],21)
        self.assertLess(sample_times(21.,27.)[-1],27)

    def test_human_6sec_rank_mapping_not_assumed_v32_short_timeline(self):
        with tempfile.TemporaryDirectory() as td:
            from top5_scene_evidence import plan
            root=Path(td)
            rows=[{"rank":5-i,"output_start_sec":6*i,
                   "output_end_sec":6*(i+1),
                   "source_sha256":hashlib.sha256(str(i).encode()).hexdigest(),
                   "source_url":f"https://pixabay.com/videos/id-{i}/",
                   "source_id":i} for i in range(5)]
            save(root/"stock_fallback/render/GENERIC_V06_QA.json",{
                "timeline":rows,"captions":["장면 검수 필요"]*5})
            result=plan("human_moments",root)
            self.assertEqual(result[0]["start"],0.)
            self.assertEqual(result[-1]["end"],30.)
            self.assertEqual([x["rank"] for x in result],[5,4,3,2,1])
            validate_plan(result)


if __name__=="__main__":
    unittest.main()
