"""Actual-source-bound video-language generator must not auto-approve captions."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_smolvlm2_editorial import (
    checks_metadata,rank_sample_times,pixel_change,
    conservative_rank_note,audit,RESOLUTION,MODEL_ID
)
from top5_standard_scene_review import VIDEO


def write(root,name,data):
    (root/name).write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")


class VideoLanguageScreenTests(unittest.TestCase):
    def _fixture(self,root):
        root=Path(root)
        (root/VIDEO).write_bytes(b"sample 30sec video protected by digest")
        video_sha=hashlib.sha256((root/VIDEO).read_bytes()).hexdigest()
        write(root,"TOPIC_RECOMMENDATIONS_V32.json",{"chosen_topic":"objects_oddities"})
        write(root,"V32_TECHNICAL_QA.json",{
            "topic":"objects_oddities","full_decode":"PASS",
            "source_count":5,"publication_approved":False})
        titles=["File:Electronic.webm","File:Kinetic art.webm",
                "File:Marble run.webm","File:Book domino.webm",
                "File:Competition chain reaction.webm"]
        raws=[{"rank":5-i,"source_page":f"https://commons.wikimedia.org/wiki/rank{i}",
               "sha256":hashlib.sha256(f"source{i}".encode()).hexdigest(),
               "rights_verified":False,"publication_approved":False} for i in range(5)]
        write(root,"SELECTED_SOURCE_PROVENANCE.json",{
            "selected":raws,"publication_approved":False})
        write(root,"SOURCE_SELECTION_REVIEW.json",{
            "items_in_rank_5_to_1_order":[{"title":titles[i],
                "source_page":raws[i]["source_page"]} for i in range(5)]})
        write(root,"V30_CREATIVE_AND_RIGHTS_GATES.json",{
            "rank_5_to_1":[{"rank":5-i,"title":titles[i],
                "caption":"장면 내용 검수 필요"} for i in range(5)]})
        write(root,"TOP5_STANDARD_EDITORIAL_QA.json",{
            "topic":"objects_oddities",
            "rendered_mp4_sha256":video_sha,
            "five_rank_source_provenance_bound":True,
            "actual_video_frames_inspected":38,
            "publication_approved":False})
        return root

    def test_ordered_real_rank_windows_within_six_seconds(self):
        starts=[{"start":2,"end":6},{"start":6,"end":11},
                {"start":11,"end":15},{"start":15,"end":21},
                {"start":21,"end":27}]
        for a in starts:
            times=rank_sample_times(a)
            self.assertEqual(times,sorted(times))
            self.assertEqual(len(times),3)
            self.assertTrue(all(a["start"] < t < a["end"] for t in times))

    def test_low_change_is_only_a_nonsemantic_warning(self):
        still=[Image.new("RGB",RESOLUTION,(80,80,80)) for _ in range(3)]
        metric=pixel_change(still)
        self.assertTrue(metric["low_motion_advisory"])
        self.assertEqual(conservative_rank_note("An object is in a room.",metric),
                         "GENERATED_TEXT_WITH_LOW_FRAME_CHANGE_REVIEW")
        moving=[Image.new("RGB",RESOLUTION,(x,x,x)) for x in (12,100,170)]
        self.assertFalse(pixel_change(moving)["low_motion_advisory"])
        with self.assertRaisesRegex(ValueError,"THREE"):
            pixel_change(still[:2])

    def test_real_source_digest_bound_export_never_approves_publication(self):
        with tempfile.TemporaryDirectory() as td:
            root=self._fixture(Path(td))
            out=root/"vlm"
            texts=[]
            def fake_reader(path,t):
                return Image.new("RGB",RESOLUTION,(int(t*8)%255,50,50))
            def fake_captioner(frames):
                texts.append(len(frames))
                return "A sequence of objects is visible. The visual change is unclear."
            result=audit(root,out,frame_reader=fake_reader,captioner=fake_captioner)
            self.assertEqual(len(texts),5)
            self.assertEqual(len(result["rows"]),5)
            self.assertEqual([x["rank"] for x in result["rows"]],[5,4,3,2,1])
            self.assertEqual(result["model"],MODEL_ID)
            self.assertFalse(result["korean_caption_ready"])
            self.assertFalse(result["automatic_caption_rendered"])
            self.assertFalse(result["publication_approved"])
            self.assertIsNone(result["score_100"])
            self.assertTrue(all(x["suggested_caption_ko"] is None for x in result["rows"]))
            self.assertTrue(all(not x["real_action_verified"] for x in result["rows"]))
            self.assertTrue((out/"VLM_SCENE_REVIEW_QUEUE.md").is_file())
            self.assertEqual(json.loads((out/"VLM_SCENE_DESCRIPTION_REVIEW.json").read_text())["rendered_video_sha256"],
                             hashlib.sha256((root/VIDEO).read_bytes()).hexdigest())

    def test_tamper_and_mismatched_topic_fail_before_model_loading(self):
        with tempfile.TemporaryDirectory() as td:
            root=self._fixture(Path(td))
            self.assertEqual(checks_metadata(root)[1],"objects_oddities")
            (root/VIDEO).write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError,"HASH"):
                checks_metadata(root)
            self._fixture(root)
            d=json.loads((root/"TOPIC_RECOMMENDATIONS_V32.json").read_text())
            d["chosen_topic"]="human_moments"
            write(root,"TOPIC_RECOMMENDATIONS_V32.json",d)
            with self.assertRaisesRegex(ValueError,"INVALID_TECHNICAL"):
                checks_metadata(root)

if __name__=="__main__":
    unittest.main()
