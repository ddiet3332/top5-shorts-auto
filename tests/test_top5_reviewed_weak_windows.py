"""Weak footage veto must be scoped to exact topic, content hash, and cut."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_auto_v30 import reviewed_weak_window,select_sources

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"review/top5_weak_source_windows.json"


class ReviewedWeakSceneTests(unittest.TestCase):
    def test_actual_nature_and_object_cut_rejections_are_scoped(self):
        rows=json.loads(REGISTRY.read_text())["rejected_windows"]
        self.assertEqual(len(rows),5)
        self.assertEqual({x["original_rank"] for x in rows if x["topic_id"] == "objects_oddities"}, {1, 2, 5})
        for row in rows:
            args=(row["topic_id"],row["title"],row["sha256"],row["start_sec"])
            self.assertIsInstance(reviewed_weak_window(*args),str)
            self.assertIsNone(reviewed_weak_window(
                "cat_surprises",row["title"],row["sha256"],row["start_sec"]))
            self.assertIsNone(reviewed_weak_window(
                row["topic_id"],row["title"],"a"*64,row["start_sec"]))
            self.assertIsNone(reviewed_weak_window(
                row["topic_id"],row["title"],row["sha256"],row["start_sec"]+2.0))
            self.assertIsNone(reviewed_weak_window(
                row["topic_id"],row["title"]+" different",row["sha256"],row["start_sec"]))
        self.assertFalse(json.loads(REGISTRY.read_text())["publication_approved"])
        self.assertTrue(all("original_rank" in x and len(x["sha256"]) == 64 for x in rows))

    def test_source_selector_skips_exact_reviewed_weak_cut_in_actual_candidate_loop(self):
        weak=json.loads(REGISTRY.read_text())["rejected_windows"][0]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            content=b"test-actual-decoded-mp4-bytes"
            digest=hashlib.sha256(content).hexdigest()
            registry=root/"bad.json"
            registry.write_text(json.dumps({"rejected_windows":[{
                **weak,"sha256":digest}]}),encoding="utf-8")
            candidates=[{"title":weak["title"],"source_page":"https://commons.wikimedia.org/weak",
                         "author":"test creator","license_url":"https://creativecommons.org/licenses/by/4.0/",
                         "license":"CC BY","title_score":5}]
            def download(source,path):
                Path(path).write_bytes(content)
            with (patch("top5_auto_v30.download_video",side_effect=download),
                  patch("top5_auto_v30.probe_duration",return_value=31.0),
                  patch("top5_auto_v30.motion_highlight",return_value=(weak["start_sec"],15)),
                  patch("top5_auto_v30.checked_scenes",return_value={}),
                  patch("top5_auto_v30.apply_curated_cut_shift",side_effect=lambda title,at,dur:at),
                  patch("top5_auto_v30.reviewed_weak_window",
                        side_effect=lambda *args: reviewed_weak_window(*args,registry_path=registry))):
                from top5_hook_selection import SourceShortage
                with self.assertRaises(SourceShortage):
                    select_sources(candidates,root,topic={"topic_id":"nature_moments","category":"자연"})
            attempts=json.loads((root/"V30_CANDIDATES.json").read_text())
            self.assertEqual(attempts[0]["status"],"REJECTED")
            self.assertIn("REVIEWED_WEAK_SOURCE_WINDOW",attempts[0]["why"])
            self.assertEqual(list((root/"originals").glob("*")),[])


if __name__=="__main__":
    unittest.main()
