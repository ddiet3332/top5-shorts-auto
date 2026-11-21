import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
import discover_new_top5 as discovery


class Provider:
    name = "fixture"

    def __init__(self, rows):
        self.rows = rows

    def search(self, query):
        return self.rows

    def download(self, item, path):
        path.write_bytes(item["id"].encode())
        return path.stat().st_size


def source(identifier, title, license_url="https://creativecommons.org/licenses/by-sa/4.0/"):
    return dict(id=identifier,title=title,license_url=license_url,license="CC",
                artist="Creator",page_url=f"https://example.org/{identifier}",mime="video/webm")


class DiscoveryGateTests(unittest.TestCase):
    def test_empty_search_produces_report_without_rendering(self):
        with TemporaryDirectory() as directory, patch.object(discovery,"assemble_video") as render:
            output = Path(directory)
            report = discovery.run("bird_actions",output,[Provider([])])
            self.assertEqual(report["reason"],"NO_CANDIDATES_FROM_PROVIDER")
            self.assertEqual(report["funnel"]["selected"],0)
            self.assertEqual(json.loads((output/"DISCOVERY_REPORT.json").read_text()),report)
            self.assertFalse(report["publication_approved"])
            render.assert_not_called()

    def test_duplicate_motion_and_unclear_action_fail_closed(self):
        rows = [source("one","File:Dog jumping.webm"),source("two","File:Dog jumping near a wall.webm"),
                source("three","File:Dog outside.webm"),source("four","File:Dog swimming.webm",
                "https://creativecommons.org/licenses/by-nc/4.0/")]

        def inspect(path, record):
            record.update(decoded=True,duration_sec=15)
            level = 200 if record["id"] == "three" else 30
            return 3.,40.,0.,1.,np.full((18,36,64),level,dtype=np.int16)

        with TemporaryDirectory() as directory, patch.object(discovery,"inspect_media",side_effect=inspect):
            report = discovery.run("dog_surprises",Path(directory),[Provider(rows)])
        self.assertEqual(report["status"],"SOURCE_SHORTAGE")
        self.assertEqual(report["funnel"]["downloaded"],3)
        self.assertEqual(report["funnel"]["rejected"],{
            "VISUAL_DUPLICATE":1,"ACTION_FAMILY_NEEDS_EDITORIAL_REVIEW":1,"LICENSE_LINK_UNSUPPORTED":1,
        })
        self.assertIn("share-alike",report["candidates"][0]["license_obligation"])

    def test_six_new_action_families_feed_shared_renderer(self):
        rows = [source(str(index),f"File:Dog {action}.webm") for index,action in enumerate(
            ("jumping","digging","fetching","swimming","rolling","shaking")
        )]

        def inspect(path, record):
            record.update(decoded=True,duration_sec=15)
            level = int(record["id"])*40
            return 3.,40.,0.,1.,np.full((18,36,64),level,dtype=np.int16)

        with TemporaryDirectory() as directory, \
             patch.object(discovery,"inspect_media",side_effect=inspect), \
             patch.object(discovery,"choose_hook",side_effect=lambda ranks,pool,*rest: pool[0]), \
             patch.object(discovery,"assemble_video",return_value=Path("review.mp4")) as render, \
             patch.object(discovery,"require_exact_video"), \
             patch.object(discovery,"technical_qa",return_value={"full_decode":"PASS"}):
            report = discovery.run("dog_surprises",Path(directory),[Provider(rows)])
            render.assert_called_once()
        self.assertEqual(report["status"],"EDITORIAL_REVIEW_REQUIRED")
        self.assertEqual(report["video"],"review.mp4")
        self.assertEqual(len({r["sha256"] for r in report["selected"]}),5)
        self.assertNotIn(report["hook"]["sha256"],{r["sha256"] for r in report["selected"]})
        self.assertFalse(report["publication_approved"])

    def test_container_tail_is_not_used_to_fill_rank(self):
        row = {"cut_start":.533,"peak_motion_sec":6.2,"duration_sec":6.733}
        self.assertEqual(discovery.fit_rank_window(row,4),2.433)


if __name__ == "__main__":
    unittest.main()
