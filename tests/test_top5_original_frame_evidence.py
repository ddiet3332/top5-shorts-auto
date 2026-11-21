"""Actual original (not composited) frame manifest bound to source hashes."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_original_frame_evidence import (
    plan,source_times,create,SIDE)
from top5_standard_scene_review import VIDEO

def put(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")

class V40OriginalFramesTests(unittest.TestCase):
    def fixture(self,root):
        root=Path(root)
        root.mkdir(parents=True,exist_ok=True)
        (root/VIDEO).write_bytes(b"composited TOP5 fake mp4")
        put(root/"TOPIC_RECOMMENDATIONS_V32.json",{"chosen_topic":"objects_oddities"})
        put(root/"V32_TECHNICAL_QA.json",{
            "topic":"objects_oddities","full_decode":"PASS",
            "source_count":5,"publication_approved":False})
        sources=[];titles=[]
        for i in range(5):
            clip=root/"originals"/f"source_{i}.webm"
            clip.parent.mkdir(exist_ok=True)
            clip.write_bytes(("source"+str(i)).encode()*14)
            title=f"File:Original rank {5-i}.webm"
            titles.append(title)
            sources.append({
                "rank":5-i,
                "source_page":f"https://commons.wikimedia.org/wiki/Rank{i}",
                "source_path":str(clip.relative_to(ROOT)),
                "sha256":hashlib.sha256(clip.read_bytes()).hexdigest(),
                "source_start_sec":2.1+i,
                "source_end_sec":8.1+i,
                "size_bytes":clip.stat().st_size,
                "rights_verified":False,"publication_approved":False,
            })
        put(root/"SELECTED_SOURCE_PROVENANCE.json",{
            "selected":sources,"publication_approved":False})
        put(root/"SOURCE_SELECTION_REVIEW.json",{
            "items_in_rank_5_to_1_order":[{
                "title":title,
                "source_page":sources[i]["source_page"]}
                for i,title in enumerate(titles)]})
        put(root/"V30_CREATIVE_AND_RIGHTS_GATES.json",{
            "rank_5_to_1":[{"rank":5-i,"title":title,
                            "caption":"장면 내용 검수 필요"}
                           for i,title in enumerate(titles)]})
        return root

    def test_selected_original_source_window_sampling(self):
        t=source_times(40.,46.)
        self.assertEqual(t,[40.42,43.,45.58])
        self.assertTrue(all(40<x<46 for x in t))
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL"):
            source_times(5,4)

    def test_five_origins_fifteen_images_no_final_overlay_and_rights_not_approved(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root=self.fixture(Path(td)/"topic_run")
            called=[]
            def fake_frame(path,t):
                called.append((str(path),t))
                return Image.new("RGB",(SIDE,SIDE),(int(t*20)%255,70,20))
            d=create(root,frame_reader=fake_frame)
            self.assertEqual(len(called),15)
            self.assertEqual(d["rank_order"],[5,4,3,2,1])
            self.assertEqual(d["original_video_frame_count"],15)
            self.assertTrue(all(len(x["image_files"])==3 for x in d["rows"]))
            self.assertFalse(d["composited_top5_text_added_to_model_images"])
            self.assertTrue(d["source_may_contain_its_own_original_labels"])
            self.assertIsNone(d["editorial_score_100"])
            self.assertFalse(d["korean_caption_approved"])
            self.assertFalse(d["source_rights_cleared"])
            self.assertFalse(d["publication_approved"])
            for row in d["rows"]:
                for x in row["image_files"]:
                    fp=root/x["relative_file"]
                    self.assertTrue(fp.is_file())
                    self.assertEqual(hashlib.sha256(fp.read_bytes()).hexdigest(),x["image_sha256"])
            self.assertTrue((root/"V40_ORIGINAL_15FRAME_STORYBOARD.jpg").is_file())
            self.assertTrue((root/"V40_ORIGINAL_FRAME_MANIFEST.json").is_file())

    def test_original_media_tampering_and_path_traversal_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root=self.fixture(Path(td)/"topic_run")
            self.assertEqual(len(plan(root)[1]),5)
            src=json.loads((root/"SELECTED_SOURCE_PROVENANCE.json").read_text())
            p=ROOT/src["selected"][0]["source_path"]
            p.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"SIZE_CHANGED|HASH_CHANGED"):
                plan(root)
            src["selected"][0]["source_path"]="../../../../etc/passwd"
            put(root/"SELECTED_SOURCE_PROVENANCE.json",src)
            with self.assertRaisesRegex(ValueError,"OUTSIDE_REPOSITORY"):
                plan(root)

if __name__=="__main__":
    unittest.main()
