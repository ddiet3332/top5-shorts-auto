"""V32 tests: fixed layout and source replacement are editorial, never rights approval."""
import hashlib
import json,sys,unittest
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_auto_v32 import CHALLENGER,add_challenger,challenger_row,apply_rank_one_story_timing,add_sofa_challenger,SOFA_CHALLENGER
from v12_sources import allowed_page
from v28_fullscreen_builder import ASS_HEAD,W,H,FPS,SEGMENTS
from top5_auto_v32 import select_v32_hook, source_digest
from top5_hook_selection import SourceShortage


class V32HookTests(unittest.TestCase):
    def select(self, folder, count=5, behavior="distinct", duration=14):
        candidates = []
        for i in range(count):
            path = folder / f"{i}.mp4"
            path.write_bytes(bytes([i]))
            candidates.append({"title":path.name, "local_path":str(path), "cut_start":4.0,
                               "duration_sec":duration, "source_page":f"https://example.com/{i}"})
        ranked = candidates[:5]
        def samples(row, start, seconds):
            level = 145 if seconds == 2 and behavior == "distinct" else 65
            size = int(seconds * 3)
            return np.broadcast_to(level + np.arange(size)[:,None,None]*2, (size,36,64))
        with patch("top5_hook_selection.sampled_frames", side_effect=samples):
            return select_v32_hook(ranked, candidates, [source_digest(Path(row["local_path"]))
                                                       for row in ranked], folder)

    def test_five_sources_choose_nonoverlapping_opening(self):
        with TemporaryDirectory() as folder:
            hook, audit, _ = self.select(Path(folder))
            self.assertEqual(hook["hook_mode"], "nonoverlapping_rank_source")
            self.assertEqual(audit["reused_rank"], 5)
            self.assertLessEqual(audit["source_end_sec"]+0.25, audit["ranked_cut_sec"][0])

    def test_sixth_source_is_preferred_and_hashed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            hook, audit, _ = self.select(root, count=6)
            self.assertTrue(audit["independent_hook"])
            self.assertEqual(hook["hook_mode"], "independent_source")
            self.assertEqual(audit["sha256"], source_digest(root / "5.mp4"))

    def test_reviewed_hook_prefers_the_byte_matched_window(self):
        with TemporaryDirectory() as folder, patch.dict(
            "top5_auto_v32.REVIEWED_HOOK_STARTS",
            {hashlib.sha256(bytes([6])).hexdigest(): 99.5},
        ):
            hook, audit, _ = self.select(Path(folder), count=7, duration=117)
            self.assertEqual(hook["title"], "6.mp4")
            self.assertEqual(audit["source_start_sec"], 99.5)
            self.assertEqual(audit["source_end_sec"], 101.5)

    def test_repeated_frames_are_rejected_even_with_time_separation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(SourceShortage):
                self.select(root, behavior="repeat")
            report = json.loads((root / "INDEPENDENT_HOOK_AUDIT.json").read_text(encoding="utf-8"))
            self.assertIn("HOOK_REPEATED_VISUALS", {row["reason_code"] for row in report["attempts"]})

    def test_no_distinct_hook_stops_with_report(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(SourceShortage, "NO_DISTINCT_HOOK"):
                self.select(root, duration=2.0)
            report = json.loads((root / "INDEPENDENT_HOOK_AUDIT.json").read_text(encoding="utf-8"))
            self.assertEqual(report["reason_code"], "NO_DISTINCT_HOOK")
            self.assertFalse(report["publication_approved"])

class V32Tests(unittest.TestCase):
    def test_locked_visual_contract(self):
        self.assertIn("Style: Caption,NanumSquare,60,",ASS_HEAD)
        self.assertIn("Style: MainTopic,NanumSquare,78,",ASS_HEAD)
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
    def test_salto_has_distinct_hook_and_story_segment(self):
        sources=[{"title":"File:Salto - Cat Jump.webm",
                  "cut_start":3.99,"duration_sec":10.07,
                  "editorial_quality_heuristic":95},
                 {"title":"File:Cat in a Bag.webm","cut_start":3.0,
                  "duration_sec":17.05}]
        chosen=apply_rank_one_story_timing(sources)
        self.assertAlmostEqual(chosen[0]["cut_start"],2.65,places=2)
        self.assertAlmostEqual(chosen[0]["hook_start"],4.9,places=2)
        self.assertLess(chosen[0]["cut_start"]+6,chosen[0]["duration_sec"])
        self.assertEqual(chosen[1]["cut_start"],3.0)
        self.assertEqual(sources[0]["cut_start"],3.99)

    def test_sofa_candidate_replaces_existing_toy_without_rights_clearance(self):
        self.assertTrue(allowed_page(SOFA_CHALLENGER))
        items=[
          {"title":"File:Cat in a Bag.webm","editorial_quality_heuristic":57},
          {"title":"Pexels PX-40826295","editorial_quality_heuristic":59},
          {"title":"File:Moomin1.webm","editorial_quality_heuristic":62},
          {"title":"File:Katzensprung in Zeitlupe.webm","editorial_quality_heuristic":64},
          {"title":"File:Salto - Cat Jump.webm","editorial_quality_heuristic":95}]
        with TemporaryDirectory() as td,patch(
            "top5_auto_v32.download_single_pexels",
            return_value={"duration_sec":15.32}):
            output,audit=add_sofa_challenger(
                {"topic_id":"cat_surprises"},items,td)
        self.assertTrue(audit["selected"])
        self.assertFalse(audit["publication_approved"])
        self.assertEqual(len(output),5)
        self.assertEqual(output[2]["label"],"소파 속 매복")
        self.assertAlmostEqual(output[2]["cut_start"],9.29)
        self.assertFalse(output[2]["rights_verified"])

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
