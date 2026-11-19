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

class AutoV29Tests(unittest.TestCase):
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
