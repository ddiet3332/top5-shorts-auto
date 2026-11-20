import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from top5_auto_v29 import CUT_LENGTHS, build_dynamic_subtitles
from top5_hook_selection import SourceShortage
from top5_reviewed_sources import select_reviewed_sources


class ReviewedDogSourcesTests(unittest.TestCase):
    def setUp(self):
        topics = json.loads((ROOT/"sample/top5_auto_topics_v30.json").read_text(encoding="utf-8"))
        self.topic = next(row for row in topics if row["topic_id"] == "dog_surprises")
        self.catalog = json.loads((ROOT/self.topic["source_catalog"]).read_text(encoding="utf-8"))

    def select(self, directory, *, unavailable=False):
        output = Path(directory)
        catalog_path = output/"catalog.json"
        for source in self.catalog["sources"]:
            source["sha256"] = hashlib.sha256(source["id"].encode()).hexdigest()
        catalog_path.write_text(json.dumps(self.catalog), encoding="utf-8")
        order = {row["title"]: i for i,row in enumerate(self.catalog["sources"])}

        def download(source, path, **kwargs):
            if unavailable:
                raise OSError("unavailable")
            path.write_bytes(source["id"].encode())
            return {"duration_sec":60}

        def frames(row, start, length):
            x = order[row["title"]]*28 + np.arange(int(length*3))[:,None,None]
            return np.broadcast_to(x, (int(length*3),36,64))

        with patch("top5_reviewed_sources.download_single_pexels", side_effect=download), \
             patch("top5_reviewed_sources.subprocess.check_output", return_value="1080,1920\n"), \
             patch("top5_reviewed_sources.sampled_frames", side_effect=frames):
            return select_reviewed_sources({**self.topic,"source_catalog":str(catalog_path)},
                                           output,list(CUT_LENGTHS.values()))

    def test_unique_rank_windows_and_readable_dog_captions(self):
        with TemporaryDirectory() as td:
            rows, _, hooks = self.select(td)
            self.assertEqual(len({row["action_family"] for row in rows}),5)
            self.assertEqual(len({row["source_page"] for row in rows}),5)
            self.assertTrue(all(row["cut_start"]<=row["payoff_sec"]<row["cut_start"]+sec
                                for row,sec in zip(rows,CUT_LENGTHS.values(),strict=True)))
            self.assertTrue(hooks[0]["reviewed_hook_only"])
            cues = build_dynamic_subtitles(Path(td)/"captions.ass",self.topic,rows,
                                           mobile_captions=True,moving_ending=True,
                                           hook_caption=hooks[0]["caption"],hook_caption_y=1712)
            self.assertIn("강아지",cues[0])
            self.assertTrue(all(r"\fs86" in cue for cue in cues if ",Caption," in cue))

    def test_missing_sources_fail_without_filler(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(SourceShortage,"SOURCE_SHORTAGE"):
                self.select(td, unavailable=True)
            audit=json.loads((Path(td)/"REVIEWED_SOURCE_SELECTION.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["selected"],[])
            self.assertEqual(len(audit["rejections"]),len(self.catalog["sources"]))
            self.assertFalse(audit["publication_approved"])
