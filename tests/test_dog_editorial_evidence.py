from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_editorial_evidence import BASELINE_SHA, captions, expected_cues, opening_motion, projected_occupancy, structural_findings


class DogEditorialEvidenceTests(unittest.TestCase):
    def layout(self):
        def clip(label,start,length):
            return (label,start,length,{"sha256":label,"cut_start":0,"playback_rate":1,"caption":label},{"action":label})
        return [clip("hook",0,2),clip("rank1",22,5),clip("outro",27,3)]

    def frames(self):
        return {key:np.full((5,3,3),i*50,dtype=np.int16)
                for i,key in enumerate(("hook","rank1","outro"))}

    def test_weak_hook_is_rejected(self):
        layout = self.layout()
        frames = self.frames()
        self.assertEqual(opening_motion(frames["hook"]),0)
        self.assertIn("WEAK_OPENING_MOTION",structural_findings(layout,frames,expected_cues(layout),0))

    def test_occupancy_projection_counts_only_visible_dog(self):
        from v28_fullscreen_builder import SourceCrop
        row = {"source_width":1000,"source_height":1800,
               "source_crop":SourceCrop(width=500,height=1200,y=100,start_x=400,end_x=400,pan_start=0,pan_end=1)}
        visible = projected_occupancy(row,(.55,.15,.85,.55),.5,True)
        clipped = projected_occupancy(row,(.2,.15,.5,.55),.5,True)
        self.assertEqual(visible["bbox_retained_fraction"],1)
        self.assertLess(clipped["bbox_retained_fraction"],.9)
        self.assertLess(clipped["visible_bbox_area_fraction"],visible["visible_bbox_area_fraction"])

    def test_ending_duplicate_even_when_hash_differs(self):
        layout = self.layout()
        frames = self.frames()
        frames["outro"] = frames["rank1"].copy()
        self.assertIn("VISUAL_DUPLICATE:rank1:outro",
                      structural_findings(layout,frames,expected_cues(layout),3))
        layout[-1][3]["sha256"] = "rank1"
        self.assertIn("SOURCE_WINDOW_REUSE:rank1:outro",
                      structural_findings(layout,frames,expected_cues(layout),3))

    def test_caption_mismatch_and_fixture_identity(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/"captions.ass"
            path.write_text("Dialogue: 5,0:00:00.00,0:00:02.00,Caption,,0,0,0,,{\\fs86}wrong\n",encoding="utf-8")
            actual = captions(path)
        self.assertEqual(actual,[(0,2,"wrong")])
        self.assertIn("CAPTION_TIMESTAMP_OR_TEXT_MISMATCH",
                      structural_findings(self.layout(),self.frames(),actual,3))
        self.assertEqual(BASELINE_SHA,"23f626c8855f26953d8dab7a8688fbe00e89d040b51da19fee1525ee9cfdc9db")


if __name__ == "__main__":
    unittest.main()
