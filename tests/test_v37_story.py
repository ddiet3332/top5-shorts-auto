"""V37: timing, story originality and CC BY-SA requirements stay explicit."""
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_auto_v32 import apply_v37_story_and_door,v37_rights_and_description
from top5_auto_v29 import build_dynamic_subtitles, rank_one_replay_start

def rows():
    return [
        {"title":"File:Cat Jumpscare.webm","editorial_quality_heuristic":58,
         "label":"기습 카메라 돌진"},
        {"title":"Pexels PX-40826295","editorial_quality_heuristic":59,
         "label":"발라당 구르기"},
        {"title":"Pexels PX-34689563","editorial_quality_heuristic":63,
         "label":"소파 속 매복"},
        {"title":"Pexels PX-17536779","editorial_quality_heuristic":64,
         "label":"상자 앞발 대결"},
        {"title":"File:Salto - Cat Jump.webm","editorial_quality_heuristic":95,
         "label":"지붕 도약"},
    ]
class V37Tests(unittest.TestCase):
    def test_door_and_story_content_are_not_legal_approval(self):
        meta={"author":"Astropulse","license":"CC BY-SA 4.0",
              "license_url":"https://creativecommons.org/licenses/by-sa/4.0"}
        with tempfile.TemporaryDirectory() as td, \
             patch("v37_cat_audition.commons_download",return_value=meta), \
             patch("top5.probe_duration",return_value=22.204):
            got,audit=apply_v37_story_and_door({"topic_id":"cat_surprises"},rows(),td)
        self.assertEqual(len(got),5)
        self.assertEqual(got[3]["title"],"File:Cat opening door.webm")
        self.assertEqual(got[3]["cut_start"],15.9)
        self.assertEqual(len(got[3]["caption_sequence"]),3)
        self.assertFalse(got[3]["publication_approved"])
        self.assertTrue(got[3]["requires_sharealike_attribution"])
        self.assertFalse(audit["rights_independently_verified"])
        self.assertFalse(audit["youtube_reused_content_approved"])
        self.assertTrue(got[1]["clear_rank_rail"])
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"captions.ass"
            build_dynamic_subtitles(file,{"headline":"고양이들의 예상 밖 행동 TOP5"},got)
            data=file.read_text(encoding="utf-8")
            self.assertIn("진짜 열렸다!",data)
            self.assertIn("몸을 일으켜 렌즈 쪽으로",data)
            self.assertIn("Style: Caption,NanumSquare,60",data)
            self.assertIn("504,1190",data)
            build_dynamic_subtitles(file,{"headline":"고양이 돌발 행동"},got,
                                    moving_ending=True,hook_caption="가만있다가 갑자기 돌진!",
                                    hook_caption_y=1620)
            self.assertIn(r"\pos(504,1620)}가만있다가 갑자기 돌진!",file.read_text(encoding="utf-8"))
            captions=[line.split(",",4) for line in file.read_text(encoding="utf-8").splitlines()
                      if line.startswith("Dialogue: ") and ",Caption," in line]
            self.assertTrue(all(left[2]<=right[1] for left,right in zip(captions,captions[1:])))
            by_text={line[4].split("}",1)[-1]:line[1:3] for line in captions}
            self.assertEqual(by_text["가만있다가 갑자기 돌진!"],["0:00:00.00","0:00:02.00"])
            self.assertEqual(by_text["몸을 일으켜 렌즈 쪽으로"][0],"0:00:04.92")
            self.assertIn("분홍 공에 앞발 한 방!",by_text)
            self.assertNotIn("장난감 낚아채기 성공!",by_text)
            self.assertEqual(by_text["지붕 사이 거리 재는 중"][1],"0:00:21.92")
            self.assertEqual(by_text["1위 장면 다시 보기"],["0:00:27.00","0:00:30.00"])
            for r in got:
                r.update({"author":"Uploader",
                          "source_page":"https://commons.wikimedia.org/wiki/"+r["title"].replace(" ","_"),
                          "license":"CC0","license_url":"https://creativecommons.org/publicdomain/zero/1.0"})
            v37_rights_and_description(got,td,audit)
            txt=(Path(td)/"V37_ATTRIBUTION_AND_PUBLISH_GATES.md").read_text()
            self.assertIn("ShareAlike",txt)
            self.assertIn("BLOCKED",txt)
    def test_failed_download_preserves_previous_candidate(self):
        with tempfile.TemporaryDirectory() as td, \
             patch("v37_cat_audition.commons_download",side_effect=RuntimeError("blocked")):
            got,audit=apply_v37_story_and_door({"topic_id":"cat_surprises"},rows(),td)
        self.assertEqual(got[3]["title"],"Pexels PX-17536779")
        self.assertFalse(audit["door_added"])
        self.assertFalse(audit["publication_approved"])
    def test_other_topic_no_unreviewed_change(self):
        got,audit=apply_v37_story_and_door({"topic_id":"dog_surprises"},rows(),"/tmp")
        self.assertEqual(got,rows())
        self.assertFalse(audit["publication_approved"])

    def test_rank_one_replay_stays_inside_original_rank_cut(self):
        self.assertAlmostEqual(rank_one_replay_start({"cut_start":2.65,"replay_offset_sec":0.9},3),3.55)
        self.assertEqual(rank_one_replay_start({"cut_start":4.0},3),5.5)
        self.assertEqual(rank_one_replay_start({"cut_start":4.0,"replay_offset_sec":9},3),7.0)
        slowed={"cut_start":2.65,"replay_offset_sec":0.9,"playback_rate":2/3}
        self.assertAlmostEqual(rank_one_replay_start(slowed,3),3.55)
        self.assertAlmostEqual(rank_one_replay_start({**slowed,"replay_offset_sec":9},3),3.65)

    def test_mobile_caption_lane_and_replay_share_the_rendered_style(self):
        selected=rows()
        selected[-1].update(mobile_caption_y=1590,caption_sequence=[[0.12,"지붕 사이로 도약 · ⅔속도"]])
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"captions.ass"
            lines=build_dynamic_subtitles(file,{"headline":"고양이 돌발 행동"},selected,
                                          moving_ending=True,mobile_captions=True,
                                          hook_caption="훅 {장면}",hook_caption_y=1455)
        captions=[line for line in lines if ",Caption," in line]
        self.assertTrue(all(r"\fs86\bord4" in line for line in captions))
        self.assertIn(r"\pos(540,1455)",captions[0])
        self.assertIn(r"훅 \{장면\}",captions[0])
        self.assertIn(r"\pos(540,1590)",captions[-1])
        self.assertTrue(captions[-2].endswith("지붕 사이로 도약 · ⅔속도"))
        self.assertTrue(captions[-1].endswith("1위 장면 다시 보기"))
if __name__=="__main__":
    unittest.main()
