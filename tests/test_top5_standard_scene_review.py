"""The ordinary mixed-topic auto renderer now yields 35 real-ranked-frame evidence."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_standard_scene_review import source_plan,evaluate_standard,VIDEO

def write(root,name,data):
    p=root/name
    p.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")

class StandardPostrenderTests(unittest.TestCase):
    def fixture(self,root,topic="nature_moments"):
        root=Path(root)
        (root/VIDEO).write_bytes(b"actual encoded video byte signature")
        write(root,"TOPIC_RECOMMENDATIONS_V32.json",{"chosen_topic":topic})
        write(root,"V32_TECHNICAL_QA.json",{
            "topic":topic,"full_decode":"PASS","source_count":5,
            "publication_approved":False})
        src=[{"rank":5-i,"source_page":f"https://commons.wikimedia.org/wiki/file{i}",
              "sha256":hashlib.sha256(f"original_{i}".encode()).hexdigest(),
              "rights_verified":False,"publication_approved":False}
             for i in range(5)]
        write(root,"SELECTED_SOURCE_PROVENANCE.json",{
            "selected":src,"publication_approved":False})
        titles=[f"File:Original Video {i}.webm" for i in range(5)]
        write(root,"SOURCE_SELECTION_REVIEW.json",{
            "items_in_rank_5_to_1_order":[
                {"title":titles[i],"source_page":src[i]["source_page"]}
                for i in range(5)]})
        write(root,"V30_CREATIVE_AND_RIGHTS_GATES.json",{
            "rank_5_to_1":[{"rank":5-i,"title":titles[i],
                            "caption":"장면 내용 검수 필요"}
                           for i in range(5)]})
        return root
    def test_exact_35_plus_3_actual_rendered_frame_evidence_preserves_publication_block(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.fixture(td)
            captures=[]
            def fake_capture(video,seconds):
                captures.append(seconds)
                # Last rank is black, making low-contrast warning a REVIEW cue.
                return Image.new("RGB",(360,640),(0,0,0) if seconds>=21 else (140,140,140))
            rep=evaluate_standard(root,capture_frame=fake_capture)
            self.assertEqual(rep["topic"],"nature_moments")
            self.assertTrue(rep["five_rank_source_provenance_bound"])
            self.assertEqual(rep["actual_video_frames_inspected"],38)
            self.assertEqual(len(captures),38)
            self.assertEqual([x["rank"] for x in rep["source_ranks"]],[5,4,3,2,1])
            self.assertEqual(rep["unready_caption_ranks"],[5,4,3,2,1])
            self.assertIn("RANK_ONE_ACTION_PAYOFF_NOT_VERIFIED",
                          rep["source_ranks"][-1]["review_flags"])
            self.assertIn("DARK_OR_CONTRAST_WEAK_SCENE_RECHECK",
                          rep["source_ranks"][-1]["review_flags"])
            self.assertIsNone(rep["editorial_score_100"])
            self.assertFalse(rep["publication_approved"])
            self.assertFalse(rep["third_party_rights_verified"])
            self.assertTrue((root/"TOP5_STANDARD_35_FRAME_QA.jpg").is_file())
            saved=json.loads((root/"TOP5_STANDARD_EDITORIAL_QA.json").read_text())
            self.assertEqual(saved["rendered_mp4_sha256"],hashlib.sha256((root/VIDEO).read_bytes()).hexdigest())
            self.assertTrue((root/"TOP5_STANDARD_EDITORIAL_QUEUE.md").is_file())
    def test_invalid_upstream_topic_is_blocked_even_with_other_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.fixture(td)
            write(root,"TOPIC_RECOMMENDATIONS_V32.json",{"chosen_topic":"unknown_fake_topic"})
            with self.assertRaisesRegex(ValueError,"TOPIC_MUST_MATCH"):
                source_plan(root)
    def test_mismatched_source_title_url_or_sha_cannot_pass_qa(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.fixture(td)
            src=json.loads((root/"SOURCE_SELECTION_REVIEW.json").read_text())
            src["items_in_rank_5_to_1_order"][0]["source_page"]="https://evil.example/mismatch"
            write(root,"SOURCE_SELECTION_REVIEW.json",src)
            with self.assertRaisesRegex(ValueError,"RANK_SOURCE_TITLE"):
                source_plan(root)
            src["items_in_rank_5_to_1_order"][0]["source_page"]="https://commons.wikimedia.org/wiki/file0"
            write(root,"SOURCE_SELECTION_REVIEW.json",src)
            original=json.loads((root/"SELECTED_SOURCE_PROVENANCE.json").read_text())
            original["selected"][0]["sha256"]=original["selected"][1]["sha256"]
            write(root,"SELECTED_SOURCE_PROVENANCE.json",original)
            with self.assertRaisesRegex(ValueError,"RANK_PROVENANCE"):
                source_plan(root)

if __name__=="__main__":
    unittest.main()
