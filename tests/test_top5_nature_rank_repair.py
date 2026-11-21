"""V57: rank edits require exact five original videos and are never rights passes."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_nature_rank_repair import apply_rank_repair
from top5_reviewed_action_captions import apply_reviewed_captions

class EvidenceBoundNatureRankTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows=[]
        self.evidence=[]
        for i in range(5):
            video=self.root/f"source{i}.webm"
            video.write_bytes(f"provenance-bound-video-source-{i}".encode())
            digest=hashlib.sha256(video.read_bytes()).hexdigest()
            row={"title":f"File:Source{i}.webm","source_page":f"https://commons.wikimedia.org/wiki/File:Source{i}.webm",
                 "local_path":str(video),"cut_start":1.25+i,
                 "rights_verified":False,"publication_approved":False,
                 "caption":"장면 내용 검수 필요"}
            self.rows.append(row)
            self.evidence.append({"sha256":digest,"title":row["title"],
                    "source_page":row["source_page"],"cut_start":row["cut_start"],
                    "observed_rank":5-i,
                    "preferred_rank":[4,3,1,2,5][i]})
        self.registry=self.root/"ranked.json"
        self.registry.write_text(json.dumps({"ranked_sources":self.evidence,
            "publication_approved":False,"source_rights_verified":False}))

    def test_all_sha_url_and_cut_matched_cohort_reorders_to_strongest_finale(self):
        result,qa=apply_rank_repair({"topic_id":"nature_moments"},
                                     self.rows,self.root,self.registry)
        self.assertEqual(qa["status"],"EXACT_FIVE_SOURCE_RANK_REORDER_REVIEW_ONLY")
        self.assertEqual([row["title"] for row in result],
                         ["File:Source4.webm","File:Source0.webm",
                          "File:Source1.webm","File:Source3.webm","File:Source2.webm"])
        self.assertEqual(qa["ranks"][-1]["previous_rank"],3)
        self.assertFalse(qa["publication_approved"])
        self.assertIsNone(qa["editorial_score_100"])

    def test_changed_original_bytes_leave_order_and_caption_untouched(self):
        Path(self.rows[1]["local_path"]).write_bytes(b"new unrelated source")
        result,qa=apply_rank_repair({"topic_id":"nature_moments"},
                                    self.rows,self.root,self.registry)
        self.assertEqual(result,self.rows)
        self.assertFalse(qa["visual_relative_strength_reordered"])

    def test_edited_original_cut_or_url_does_not_inherit_rank(self):
        self.rows[0]["cut_start"]+=.25
        _,qa=apply_rank_repair({"topic_id":"nature_moments"},
                                self.rows,self.root,self.registry)
        self.assertFalse(qa["visual_relative_strength_reordered"])
        self.rows[0]["cut_start"]-=.25
        self.rows[0]["source_page"]="https://wrong.invalid/source"
        _,qa=apply_rank_repair({"topic_id":"nature_moments"},
                                self.rows,self.root,self.registry)
        self.assertFalse(qa["visual_relative_strength_reordered"])

    def test_other_topic_stays_original(self):
        rows,qa=apply_rank_repair({"topic_id":"cat_surprises"},
                                   self.rows,self.root,self.registry)
        self.assertEqual(rows,self.rows)
        self.assertFalse(qa["visual_relative_strength_reordered"])

    def test_reviewed_4sec_explosion_has_six_second_rank_one_bounded_playback(self):
        ordered,qa=apply_rank_repair({"topic_id":"nature_moments"},
                                     self.rows,self.root,self.registry)
        stories=self.root/"stories.json"
        stories.write_text(json.dumps({"stories":[{
            "topic_id":"nature_moments","title":self.evidence[2]["title"],
            "source_page":self.evidence[2]["source_page"],
            "sha256":self.evidence[2]["sha256"],
            "start_sec":self.evidence[2]["cut_start"],
            "cut_tolerance_sec":0.12,
            "original_rank":3,"seconds":4,
            "caption_sequence":[[.12,"위성에서 번지는 분출"],[1.48,"구름이 넓어지고 있다"]],
            "rights_verified":False,"publication_approved":False,
            "full_action_verified":False}]}))
        rendered,audit=apply_reviewed_captions(
            {"topic_id":"nature_moments"},ordered,self.root,stories)
        self.assertEqual(rendered[-1]["title"],"File:Source2.webm")
        self.assertAlmostEqual(rendered[-1]["playback_rate"],2/3,places=6)
        self.assertAlmostEqual(rendered[-1]["source_reviewed_end_sec"],
                               self.rows[2]["cut_start"]+4)
        self.assertAlmostEqual(rendered[-1]["caption_sequence"][1][0],2.22)
        self.assertFalse(audit["publication_approved"])
        self.assertEqual(audit["sample_grounded_caption_ranks"],[1])

    def test_builtin_v56_evidence_covers_five_distinct_source_hashes(self):
        path=Path(__file__).resolve().parents[1]/"review/top5_v56_nature_rank_evidence.json"
        e=json.loads(path.read_text())
        self.assertEqual(len(e["ranked_sources"]),5)
        self.assertEqual(len({x["sha256"] for x in e["ranked_sources"]}),5)
        self.assertEqual({x["preferred_rank"] for x in e["ranked_sources"]},
                         {1,2,3,4,5})
        self.assertEqual(next(x["title"] for x in e["ranked_sources"]
                          if x["preferred_rank"]==1),
                         "File:Tonga Volcano Eruption 2022-01-15 0320Z to 0610Z Himawari-8 visible.webm")
        self.assertFalse(e["publication_approved"])
        self.assertIsNone(e["editorial_score_100"])

if __name__=="__main__": unittest.main()
