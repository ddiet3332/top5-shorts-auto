import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0,"src")
from top5_free_visual_metrics import analyze

class VisualMetricsTests(unittest.TestCase):
    def test_identical_frames_are_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            frames=[]
            for i in range(5):
                path=root/f"{i}.png"
                Image.new("RGB",(90,160),"white").save(path)
                frames.append({"time_seconds":i,"path":str(path)})
            manifest=root/"frames.json"
            manifest.write_text(json.dumps({"frames":frames}))
            result=analyze(manifest,root/"out.json")
            self.assertTrue(result["possible_static_or_repetitive_visuals"])
            self.assertEqual(result["very_similar_adjacent_pairs"],4)
            self.assertIsNone(result["editorial_score_100"])
    def test_missing_frame_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            manifest=root/"frames.json"
            manifest.write_text(json.dumps({"frames":[{"path":str(root/f"{i}.png")} for i in range(5)]}))
            with self.assertRaises(FileNotFoundError):
                analyze(manifest,root/"out.json")

if __name__=="__main__":
    unittest.main()
