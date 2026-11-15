"""V24 requires exact new source URLs, no duplicate old low-payoff footage."""
import json,sys,unittest
from tempfile import TemporaryDirectory
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from v24_new_source_audition import checked_catalog,report_audition
from publish_v24_index import summary

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"sample/v24-new-candidates.json"

class V24Tests(unittest.TestCase):
    def test_verified_pages_and_three_new_action_classes(self):
        rows=checked_catalog(CATALOG)
        self.assertEqual(len(rows),3)
        self.assertEqual({x["id"] for x in rows},
                         {"PX-5991137","PX-13673047","PX-32486247"})
        self.assertEqual(len({x["action_group"] for x in rows}),3)
        self.assertTrue(all(x["publication_approved"] is False for x in rows))
        self.assertTrue(all(x["source_audio_approved"] is False for x in rows))
    def test_no_preview_no_publication_or_score(self):
        with TemporaryDirectory() as d:
            r=report_audition(checked_catalog(CATALOG),[],Path(d))
            self.assertEqual(r["preview_count"],0)
            self.assertIsNone(r["final_content_score"])
            self.assertFalse(r["publication_approved"])
            pointer=summary(r,repo="ddiet3332/top5-shorts-auto",
                            run_id=100,run_number=1,build_result="success")
            self.assertFalse(pointer["publication_approved"])
            self.assertFalse(pointer["rights_verified"])
            self.assertEqual(pointer["preview_windows"],0)
    def test_no_reused_previous_weak_footage(self):
        rows=json.loads(CATALOG.read_text(encoding="utf-8"))
        rows[0]["id"]="PX-5495527"
        with TemporaryDirectory() as d:
            p=Path(d)/"catalog.json";p.write_text(json.dumps(rows),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"low-payoff"):
                checked_catalog(p)
    def test_no_conflated_rank_from_same_source(self):
        rows=json.loads(CATALOG.read_text(encoding="utf-8"))
        rows[1]=dict(rows[0])
        with TemporaryDirectory() as d:
            p=Path(d)/"catalog.json";p.write_text(json.dumps(rows),encoding="utf-8")
            with self.assertRaises(ValueError):
                checked_catalog(p)
if __name__=="__main__":unittest.main()
