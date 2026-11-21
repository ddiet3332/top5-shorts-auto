"""V55: independently verify 15-row nature cap no longer hides available event footage.

These tests mock only network and FFmpeg; all ranking/diversity logic is real.
Source metadata and brightness/motion proxies NEVER mean editorial or rights QA.
"""
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from top5_auto_v30 import select_sources,NATURE_MAX_DOWNLOAD_ATTEMPTS
from top5_candidate_visual_gate import nature_event_family
from top5_hook_selection import SourceShortage


class BroaderNatureSourceScreeningTests(unittest.TestCase):
    def source(self,name,i):
        return {
            "title":name,
            "source_page":f"https://commons.wikimedia.org/wiki/File:Test_{i}",
            "author":f"Creator {i}","license":"CC BY 4.0",
            "license_url":"https://creativecommons.org/licenses/by/4.0/",
            "title_score":8.0,"discovery_rank":12.0,
        }

    def patches(self,weak):
        def fake_download(_downloader,row,path):
            # The wrapper receives the underlying downloader, source and path.
            Path(path).write_bytes(row["title"].encode("utf-8"))
        return (
            patch("top5_auto_v30.download_with_bounded_retry",side_effect=fake_download),
            patch("top5_auto_v30.probe_duration",return_value=17.0),
            patch("top5_auto_v30.motion_highlight",return_value=(2.0,15.0)),
            patch("top5_auto_v30.inspect_original_window",
                return_value={"mostly_dark":False,"near_dark_count":0}),
            patch("top5_auto_v30.checked_scenes",return_value={}),
            patch("top5_auto_v30.reviewed_weak_window",
                side_effect=lambda _topic,title,_sha,_time: "VERIFIED_WEAK_CUT" if title in weak else None)
        )

    def test_five_families_after_fifteenth_candidate_are_actually_reached(self):
        self.assertGreaterEqual(NATURE_MAX_DOWNLOAD_ATTEMPTS,20)
        bad=[f"File:Weak distraction {i}.webm" for i in range(15)]
        useful=[
            "File:Aurora Borealis in Norway.webm",
            "File:Lightning storm over sea.webm",
            "File:Tonga Volcano eruption.webm",
            "File:Strokkur geyser eruption.webm",
            "File:Ocean wave crashing.webm",
        ]
        sources=[self.source(title,i) for i,title in enumerate([*bad,*useful])]
        with tempfile.TemporaryDirectory() as temp:
            with self.patches(set(bad))[0], self.patches(set(bad))[1], self.patches(set(bad))[2], self.patches(set(bad))[3], self.patches(set(bad))[4], self.patches(set(bad))[5]:
                chosen,attempts=select_sources(
                    sources,Path(temp),topic={"topic_id":"nature_moments","category":"자연"})
            report=json.loads((Path(temp)/"V30_SOURCE_SCREENING_SPAN_QA.json").read_text())
        self.assertEqual(len(chosen),5)
        self.assertEqual(len({nature_event_family(r["title"]) for r in chosen}),5)
        self.assertEqual(report["attempted_candidate_count"],20)
        self.assertEqual(report["uninspected_metadata_candidates"],0)
        self.assertEqual(report["metadata_candidate_count"],20)
        self.assertEqual(report["distinct_known_nature_event_family_count"],5)
        self.assertFalse(report["publication_approved"])

    def test_limited_budget_is_explicit_not_false_claim_of_global_source_shortage(self):
        self.assertEqual(NATURE_MAX_DOWNLOAD_ATTEMPTS,32)
        bad=[f"File:Weak distraction {i}.webm" for i in range(32)]
        unseen=[f"File:Lightning storm after budget {i}.webm" for i in range(12)]
        sources=[self.source(x,i) for i,x in enumerate([*bad,*unseen])]
        with tempfile.TemporaryDirectory() as td:
            with self.patches(set(bad))[0], self.patches(set(bad))[1], self.patches(set(bad))[2], self.patches(set(bad))[3], self.patches(set(bad))[4], self.patches(set(bad))[5]:
                with self.assertRaises(SourceShortage):
                    select_sources(sources,Path(td),topic={
                        "topic_id":"nature_moments","category":"자연"})
            qa=json.loads((Path(td)/"V30_SOURCE_SCREENING_SPAN_QA.json").read_text())
            self.assertEqual(qa["metadata_candidate_count"],44)
            self.assertEqual(qa["attempted_candidate_count"],32)
            self.assertEqual(qa["uninspected_metadata_candidates"],12)
            self.assertTrue(qa["remaining_metadata_not_conclusive_inventory"])
            self.assertFalse(qa["publication_approved"])

    def test_three_consecutive_429s_circuit_break_even_with_expanded_budget(self):
        candidates=[
            self.source(f"File:Aurora Borealis source {i}.webm",i)
            for i in range(22)]
        def rate_limit(*_args,**_kw):
            raise urllib.error.HTTPError(
                "https://upload.wikimedia.org/test",429,
                "Too Many Requests",{},None)
        with tempfile.TemporaryDirectory() as td:
            with (patch("top5_auto_v30.download_with_bounded_retry",side_effect=rate_limit),
                  patch("top5_auto_v30.checked_scenes",return_value={})):
                with self.assertRaises(SourceShortage):
                    select_sources(candidates,Path(td),topic={
                        "topic_id":"nature_moments","category":"자연"})
            qa=json.loads((Path(td)/"V30_SOURCE_SCREENING_SPAN_QA.json").read_text())
            self.assertEqual(qa["attempted_candidate_count"],3)
            self.assertTrue(qa["provider_circuit_breaker_tripped"])
            self.assertEqual(qa["provider_error_candidate_count"],3)
            self.assertEqual(qa["uninspected_metadata_candidates"],19)
            self.assertFalse(qa["publication_approved"])

if __name__=="__main__":
    unittest.main()
