"""V50 visually sampled stories cannot leak onto other source bytes/offsets."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_reviewed_action_captions import apply_reviewed_captions

def make_base(root):
    rows=[]
    entries=[]
    for i in range(5):
        src=root/f"rank_{5-i}.webm"
        src.write_bytes(f"original-media-{i}".encode())
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        row={"local_path":str(src),"title":f"File:Real{i}.webm",
             "source_page":f"https://commons.wikimedia.org/wiki/File:Real{i}.webm",
             "cut_start":round(i*.5,2),"caption":"장면 내용 검수 필요",
             "label":"자연 장면 검수 필요",
             "rights_verified":False,"publication_approved":False}
        rows.append(row)
        entries.append({"topic_id":"nature_moments","original_rank":5-i,
            "title":row["title"],"source_page":row["source_page"],
            "sha256":digest,"start_sec":row["cut_start"],"cut_tolerance_sec":.12,
            "seconds":(4 if i in (0,2) else 5 if i==1 else 6),
            "caption_sequence":[[.1,"화면에서 확인한 장면"],[1.1,"실제로 움직이는 장면"]],
            "rights_verified":False,"publication_approved":False,
            "full_action_verified":False})
    registry=root/"stories.json"
    registry.write_text(json.dumps({"stories":entries},ensure_ascii=False))
    return rows,registry

class VerifiedCutCaptionsTests(unittest.TestCase):
    def test_exact_source_time_topic_rank_allows_grounded_captions(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x); rows,registry=make_base(root)
            selected,qa=apply_reviewed_captions({"topic_id":"nature_moments"},rows,root,registry)
            self.assertEqual(qa["sample_grounded_caption_ranks"],[5,4,3,2,1])
            self.assertEqual(selected[0]["caption_sequence"][1][1],"실제로 움직이는 장면")
            self.assertFalse(qa["five_ranks_story_verified"])
            self.assertIsNone(qa["editorial_score_100"])
            self.assertFalse(qa["publication_approved"])

    def test_new_video_sha_blocks_reused_story(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x);rows,registry=make_base(root)
            Path(rows[0]["local_path"]).write_bytes(b"new unrelated video")
            selected,qa=apply_reviewed_captions({"topic_id":"nature_moments"},rows,root,registry)
            self.assertEqual(qa["unmatched_caption_ranks"],[5])
            self.assertEqual(selected[0]["caption"],"장면 내용 검수 필요")
            self.assertNotIn("caption_sequence",selected[0])

    def test_different_cut_does_not_inherit_previous_scene_description(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x);rows,registry=make_base(root)
            rows[0]["cut_start"]+=.5
            selected,qa=apply_reviewed_captions({"topic_id":"nature_moments"},rows,root,registry)
            self.assertEqual(qa["unmatched_caption_ranks"],[5])
            self.assertEqual(selected[0]["caption"],"장면 내용 검수 필요")

    def test_other_subject_does_not_inherit_nature_story(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x);rows,registry=make_base(root)
            selected,qa=apply_reviewed_captions({"topic_id":"human_moments"},rows,root,registry)
            self.assertEqual(qa["sample_grounded_caption_ranks"],[])
            self.assertEqual(len(qa["unmatched_caption_ranks"]),5)
            self.assertFalse(qa["publication_approved"])

    def test_rank_reordering_and_source_page_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x);rows,registry=make_base(root)
            rows[0]["source_page"]="https://evil.example/steal"
            rows[1]["title"]="File:Different.webm"
            selected,qa=apply_reviewed_captions({"topic_id":"nature_moments"},rows,root,registry)
            self.assertEqual(qa["unmatched_caption_ranks"],[5,4])
            self.assertEqual(selected[1]["caption"],"장면 내용 검수 필요")

    def test_reviews_cannot_grant_rights_or_verified_85_score(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x);rows,registry=make_base(root)
            doc=json.loads(registry.read_text())
            doc["stories"][0]["publication_approved"]=True
            registry.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,"CANNOT_GRANT_RIGHTS"):
                apply_reviewed_captions({"topic_id":"nature_moments"},rows,root,registry)

if __name__=="__main__":
    unittest.main()
