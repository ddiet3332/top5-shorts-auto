"""Model may describe originals, but no text-only result can approve captions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from test_top5_original_frame_evidence import V40OriginalFramesTests
from top5_original_frame_evidence import create,SIDE
from top5_v41_original_source_vlm import run,load_true_original_frame_inputs

class OriginalSourceModelTests(unittest.TestCase):
    def _real_fixture(self,folder):
        root=V40OriginalFramesTests().fixture(Path(folder)/"topic_run")
        def reader(path,second):
            return Image.new("RGB",(SIDE,SIDE),(int(second*20)%255,20,120))
        create(root,frame_reader=reader)
        return root

    def test_five_original_source_verified_rank_images_and_no_captions(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root=self._real_fixture(td)
            self.assertEqual(load_true_original_frame_inputs(root)[1],"objects_oddities")
            called=[]
            def captioner(images):
                called.append(len(images))
                return "A ball runs over a small track while people watch."
            report=run(root,root/"original_model",captioner=captioner)
            self.assertEqual(called,[3,3,3,3,3])
            self.assertEqual([r["rank"] for r in report["rows"]],[5,4,3,2,1])
            self.assertTrue(report["input_frames_original_source"])
            self.assertFalse(report["top5_template_text_present_in_input"])
            self.assertFalse(report["publication_approved"])
            self.assertFalse(report["korean_caption_ready"])
            self.assertFalse(report["real_action_verified"])
            self.assertIsNone(report["score_100"])
            self.assertTrue(all(r["suggested_caption_ko"] is None for r in report["rows"]))
            self.assertTrue(all(not r["original_creative_caption_approved"] for r in report["rows"]))
            self.assertTrue(all(len(r["frame_jpeg_sha256"])==3 for r in report["rows"]))
            self.assertTrue((root/"original_model"/"V41_ORIGINAL_FRAME_REVIEW.md").is_file())
    def test_original_rank_frame_mutation_and_traversal_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root=self._real_fixture(td)
            data=json.loads((root/"V40_ORIGINAL_FRAME_MANIFEST.json").read_text())
            row=data["rows"][0]
            jpg=root/row["image_files"][0]["relative_file"]
            jpg.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"ORIGINAL_FRAME_SHA_MISMATCH"):
                load_true_original_frame_inputs(root)
            data["rows"][0]["image_files"][0]["relative_file"]="../../../../outside.jpg"
            (root/"V40_ORIGINAL_FRAME_MANIFEST.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"ORIGINAL_FRAME_PATH_TRAVERSAL"):
                load_true_original_frame_inputs(root)
    def test_model_is_never_allowed_to_claim_false_rights_via_manifest(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            root=self._real_fixture(td)
            data=json.loads((root/"V40_ORIGINAL_FRAME_MANIFEST.json").read_text())
            data["publication_approved"]=True
            (root/"V40_ORIGINAL_FRAME_MANIFEST.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"ORIGINAL_EVIDENCE_UNTRUSTED"):
                load_true_original_frame_inputs(root)

if __name__=="__main__":
    unittest.main()
