"""V58: independent 2s hook candidates must include screened, unranked originals."""
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_auto_v30 import select_sources
from top5_auto_v32 import select_v32_hook
from top5_hook_selection import identity

class ScreenedUnrankedHookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        titles=[
            "File:Aurora Norway.webm",
            "File:Strokkur geyser eruption.webm",
            "File:Garone River overflow.webm",
            "File:Tonga Volcano eruption.webm",
            "File:Kawaida Waterfall cascading.webm",
            "File:Dark Aurora Borealis.webm",
            "File:Flooding rain river.webm",
            "File:Yellowstone geyser eruption.webm",
            "File:Lightning Storm at sea.webm"]
        self.metadata=[{"title":t,
            "source_page":f"https://commons.wikimedia.org/wiki/File:Hook_{i}.webm",
            "author":f"author{i}",
            "license":"CC BY 4.0",
            "license_url":"https://creativecommons.org/licenses/by/4.0/",
            "title_score":7.0} for i,t in enumerate(titles)]

    def screen(self):
        def download(_downloader,source,path,**_):
            Path(path).write_bytes(source["title"].encode())
        with ExitStack() as stack:
            for name,kwargs in [
                ("download_with_bounded_retry",{"side_effect":download}),
                ("probe_duration",{"return_value":16.0}),
                ("motion_highlight",{"return_value":(3.0,12.0)}),
                ("inspect_original_window",{"return_value":{"mostly_dark":False,"near_dark_count":0}}),
                ("checked_scenes",{"return_value":{}}),
                ("reviewed_weak_window",{"return_value":None})
            ]:
                stack.enter_context(patch("top5_auto_v30."+name,**kwargs))
            reserve=[]
            selected,attempts=select_sources(
                self.metadata,self.root,topic={
                    "topic_id":"nature_moments","category":"자연"},
                reserve_pool=reserve)
            return selected,reserve,attempts

    def test_all_nine_originals_survive_rank_pruning_for_hook_audition(self):
        selected,reserve,attempts=self.screen()
        self.assertEqual(len(selected),5)
        self.assertEqual(len(reserve),9)
        self.assertEqual(len({identity(r) for r in reserve}),9)
        selected_ids={identity(r) for r in selected}
        self.assertGreaterEqual(
            len([x for x in reserve if identity(x) not in selected_ids]),4)
        qa=json.loads((self.root/"V58_HOOK_RESERVE_POOL_QA.json").read_text())
        self.assertEqual(qa["screened_original_source_count"],9)
        self.assertEqual(qa["five_ranked_source_count"],5)
        self.assertEqual(qa["independent_unranked_source_count"],4)
        self.assertFalse(qa["publication_approved"])
        self.assertFalse(qa["actual_hook_scene_pass"])

    def test_source_hash_bound_hook_sees_independent_candidate_first(self):
        selected,reserve,_=self.screen()
        sha=[hashlib.sha256(Path(r["local_path"]).read_bytes()).hexdigest()
             for r in selected]
        chosen=[]
        def pick(_ranked,candidates,_durations,attempts):
            selected_ids={identity(r) for r in selected}
            independents=[r for r in candidates
                          if identity(r) not in selected_ids]
            self.assertEqual(len(independents),4)
            chosen.extend(independents)
            return {**independents[0],"hook_start":.2,
                    "hook_mode":"independent_source"}
        with patch("top5_auto_v32.choose_hook",side_effect=pick):
            hook,audit,path=select_v32_hook(selected,reserve,sha,self.root)
        self.assertTrue(audit["independent_hook"])
        self.assertEqual(audit["hook_mode"],"independent_source")
        self.assertEqual(hook["source_page"],chosen[0]["source_page"])
        self.assertFalse(audit["publication_approved"])
        self.assertFalse(audit["editorial_action_verified"])

    def test_no_false_independent_hook_success_without_screened_clip(self):
        selected,reserve,_=self.screen()
        sha=[hashlib.sha256(Path(r["local_path"]).read_bytes()).hexdigest()
             for r in selected]
        # No unranked original is supplied. Selection may be possible from
        # nonoverlapping ranked content, but its independent flag is false.
        def pick(_ranked,candidates,_durations,attempts):
            return {**selected[0],"hook_start":0,
                    "hook_mode":"nonoverlapping_rank_source"}
        with patch("top5_auto_v32.choose_hook",side_effect=pick):
            _hook,audit,_path=select_v32_hook(selected,selected,sha,self.root)
        self.assertFalse(audit["independent_hook"])
        self.assertFalse(audit["publication_approved"])

if __name__=="__main__":
    unittest.main()
