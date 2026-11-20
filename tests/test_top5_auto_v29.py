"""Unit tests for V29 auto topic, entitlement, and user's locked layout."""
import json
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_auto_v29 import title_score, story_label, build_dynamic_subtitles, CUT_LENGTHS
from v28_fullscreen_builder import ASS_HEAD, SEGMENTS, W, H, FPS
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from top5_auto_v29 import select_sources
from top5_hook_selection import SourceShortage, separated

class AutoV29Tests(unittest.TestCase):
    def select_fixture(self, count, repeated=False):
        candidates=[{"title":f"{term} {i}.mp4","title_score":10-i}
                    for i,term in enumerate(("jump","chase","spin","fall","play","startled")[:count])]
        def sample(row,start,seconds):
            # Uniform synthetic luminance values stand in for two distinct moving sequences.
            base=40+10*int(Path(row["local_path"]).stem.split("_")[1])
            if seconds == 2 and not repeated:
                base=145
            return np.broadcast_to(np.arange(int(seconds*3))[:,None,None]*2+base,(int(seconds*3),36,64))
        with TemporaryDirectory() as folder, patch("top5_auto_v29.download_video"), \
             patch("top5_auto_v29.probe_duration",return_value=19.0), \
             patch("top5_auto_v29.motion_highlight",return_value=(5,18)), \
             patch("top5_hook_selection.sampled_frames",side_effect=sample):
            return select_sources(candidates,Path(folder))

    def test_five_sources_use_a_separated_hook(self):
        ranked,_,hook=self.select_fixture(5)
        self.assertEqual(hook["hook_mode"],"nonoverlapping_rank_source")
        index=next(i for i,row in enumerate(ranked) if row["title"]==hook["title"])
        self.assertTrue(separated(hook["hook_start"],ranked[index]["cut_start"],list(CUT_LENGTHS.values())[index]))

    def test_six_sources_prefer_an_independent_hook(self):
        ranked,_,hook=self.select_fixture(6)
        self.assertEqual(hook["hook_mode"],"independent_source")
        self.assertNotIn(hook["title"],{row["title"] for row in ranked})

    def test_repeated_visuals_fail_even_in_separate_time_windows(self):
        with self.assertRaises(SourceShortage) as issue:
            self.select_fixture(5,repeated=True)
        self.assertEqual(issue.exception.code,"NO_DISTINCT_HOOK")
        self.assertTrue(any(x.get("reason_code")=="HOOK_REPEATED_VISUALS" for x in issue.exception.attempts))

    def test_locked_design(self):
        self.assertIn("Style: Caption,NanumSquare,60,",ASS_HEAD)
        self.assertIn("Style: MainTopic,NanumSquare,78,",ASS_HEAD)
        self.assertEqual((W,H,FPS),(1080,1920,24))
        self.assertEqual(sum(sec for _,sec in SEGMENTS),30)
        self.assertEqual(CUT_LENGTHS["rank1"],6)

    def test_topic_is_broad(self):
        topics=json.loads((ROOT/"sample/top5_auto_topics.json").read_text())
        self.assertGreaterEqual(len(topics),5)
        self.assertEqual(set(t["category"] for t in topics),
            {"동물","자연","사물","사람"})
        self.assertLessEqual(max(map(lambda t:len(t["headline"]),topics)),13)

    def test_source_filters(self):
        topic=json.loads((ROOT/"sample/top5_auto_topics.json").read_text())[0]
        base={"title":"File:Cat jumpscare.webm","license":"CC0",
              "license_url":"https://creativecommons.org/publicdomain/zero/1.0",
              "author":"Uploader","size_bytes":1000000,"source_claim":"Own work"}
        self.assertGreater(title_score(base,topic),0)
        self.assertLess(title_score({**base,"title":"File:Unrelated waterfall.webm"},topic),0)
        self.assertLess(title_score({**base,"source_claim":"Repost from Vimeo"},topic),0)
        self.assertLess(title_score({**base,"author":""},topic),0)

    def test_video_specific_text_uses_same_overlay(self):
        topic={"headline":"고양이 돌발 행동"}
        items=[{"label":n} for n in
               ["실수","추격전","깜짝 반응","도약","장난감 놀이"]]
        with TemporaryDirectory() as t:
            out=Path(t)/"dynamic.ass"
            lines=build_dynamic_subtitles(out,topic,items)
            content=out.read_text(encoding="utf-8")
            self.assertIn("Style: Caption,NanumSquare,60,",content)
            self.assertIn(r"\pos(540,112)}{\fs82\bord3}고양이 돌발 행동",content)
            self.assertIn(r"\pos(540,220)}{\fs100\bord2}TOP5",content)
            self.assertIn("504,1190",content)
            self.assertEqual(sum(",Caption," in x for x in lines),6)
            self.assertIn("고양이 돌발 행동",content)
            self.assertEqual(sum(",MainTopic," in x for x in lines),1)
            self.assertEqual(sum(",TopFive," in x for x in lines),1)

if __name__=="__main__":
    unittest.main()
