"""V32 tests: fixed layout and source replacement are editorial, never rights approval."""
import json,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_auto_v32 import CHALLENGER,add_challenger,challenger_row
from v12_sources import allowed_page
from v28_fullscreen_builder import ASS_HEAD,W,H,FPS,SEGMENTS

class V32Tests(unittest.TestCase):
    def test_locked_visual_contract(self):
        self.assertIn("Style: Caption,NanumSquare,60,",ASS_HEAD)
        self.assertIn("Style: MainTopic,NanumSquare,59,",ASS_HEAD)
        self.assertEqual((W,H,FPS),(1080,1920,24))
        self.assertEqual(sum(n for _,n in SEGMENTS),30)
    def test_curation_page_allowlisted(self):
        self.assertTrue(allowed_page(CHALLENGER))
        self.assertFalse(allowed_page({**CHALLENGER,
            "page_url":"https://videos.unknown-site.example.com/bad"}))
    def test_one_source_replaces_only_weakest(self):
        base=[
          {"title":"File:Slow Two Cats.webm","editorial_quality_heuristic":51},
          {"title":"File:Cat in a Bag.webm","editorial_quality_heuristic":57},
          {"title":"File:Moomin1.webm","editorial_quality_heuristic":62},
          {"title":"File:Grass Cat.webm","editorial_quality_heuristic":64},
          {"title":"File:Salto - Cat Jump.webm","editorial_quality_heuristic":95}]
        with TemporaryDirectory() as tmp,patch(
            "top5_auto_v32.download_single_pexels",
            return_value={"duration_sec":21.67}):
            result,status=add_challenger({"topic_id":"cat_surprises"},base,tmp)
            self.assertTrue(status["download_ok"])
            self.assertFalse(status["publication_approved"])
            self.assertEqual(status["replaced"],"File:Slow Two Cats.webm")
            self.assertEqual(result[1]["label"],"발라당 구르기")
            self.assertEqual(len(result),5)
            self.assertEqual(len({x["title"] for x in result}),5)
            self.assertFalse(result[1]["rights_verified"])
    def test_unrelated_topic_is_unchanged(self):
        items=[{"title":str(i)} for i in range(5)]
        with TemporaryDirectory() as tmp:
            result,status=add_challenger({"topic_id":"nature_moments"},items,tmp)
        self.assertEqual(result,items)
        self.assertFalse(status["attempted"])
    def test_rights_held_in_new_row(self):
        item=challenger_row(CHALLENGER,Path("/fake/source.mp4"),
                            {"duration_sec":21.67})
        self.assertFalse(item["publication_approved"])
        self.assertFalse(item["provenance_independently_verified"])
        self.assertEqual(item["cut_start"],0)
        self.assertEqual(item["license"],"Pexels License")
        self.assertNotEqual(item["license"],"CC BY")

if __name__=="__main__":unittest.main()
