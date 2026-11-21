"""Ensure unattended replacement reporting never fabricates clearance or scores."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dog_replacement_report import report


class ReportTests(unittest.TestCase):
    def test_fresh_provider_previews_change_next_action_not_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            profile={"shots":{
                "hook":{"source_id":"A","action":"jump"},
                "rank5":{"source_id":"B","action":"leap"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"E","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            files = [root/"profile.json",root/"old.json",root/"pixabay.json",root/"commons.json"]
            payloads = [profile,{"candidates":[]},
                {"provider":"pixabay","candidates":[{
                    "id":"PB-123","status":"PREVIEW_READY_REVIEW_REQUIRED",
                    "rights_status":"UNVERIFIED","editorial_score":None}]},
                {"provider":"wikimedia_commons","candidates":[{
                    "id":"CM-abcdef123456","status":"AUDITION_FAILED"}]}]
            for file,payload in zip(files,payloads):
                file.write_text(json.dumps(payload),encoding="utf-8")
            result=report(files[0],files[1],provider_reports=files[2:])
            self.assertEqual(result["candidate_count"],0)
            self.assertEqual(result["provider_preview_count"],1)
            self.assertEqual(result["provider_preview_ids_pending_review"],["PB-123"])
            self.assertEqual(result["next_action"],"REVIEW_NEW_PREVIEWS")
            self.assertIsNone(result["editorial_score"])
            self.assertFalse(result["publication_approved"])
            self.assertTrue(all(d["status"]=="NO_UPGRADE" for d in result["decisions"]))

    def test_cached_review_queue_is_pending_not_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            profile={"shots":{
                "hook":{"source_id":"A","action":"jump"},
                "rank5":{"source_id":"B","action":"leap"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"E","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            p=root/"profile.json"
            p.write_text(json.dumps(profile))
            old=root/"old.json"
            old.write_text(json.dumps({"candidates":[]}))
            cached=root/"pixabay.json"
            cached.write_text(json.dumps({"provider":"pixabay","candidates":[
                {"id":"PB-111","status":"PREVIEW_READY_REVIEW_REQUIRED",
                 "preview_origin":"CACHED_PREVIOUS_RUN","publication_approved":False}]}))
            result=report(p,old,provider_reports=[cached])
            self.assertEqual(result["provider_preview_count"],1)
            self.assertEqual(result["provider_preview_new_count"],0)
            self.assertEqual(result["provider_preview_cached_count"],1)
            self.assertEqual(result["next_action"],"REVIEW_PENDING_PREVIEWS")
            self.assertFalse(result["publication_approved"])
            self.assertIsNone(result["editorial_score"])

    def test_incumbent_scores_require_real_frame_review_fields(self):
        from dog_replacement_report import incumbent_reviews, RUBRIC
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            profile={"shots":{"rank5":{"source_id":"A"},"rank2":{"source_id":"B"}}}
            payload={"schema_version":1,"review_kind":"incumbent_rank_segment_scoring",
                     "rubric_version":"dog_rank_segment_v1","publication_approved":False,
                     "max_points":RUBRIC,
                     "ranks":{"rank5":{"source_id":"A","reviewed_frames":False,"points":None},
                              "rank2":{"source_id":"B","reviewed_frames":False,"points":None}}}
            path=root/"scores.json"
            path.write_text(json.dumps(payload))
            scores, blockers=incumbent_reviews(profile,path)
            self.assertEqual(scores,{"rank5":None,"rank2":None})
            self.assertEqual(len(blockers),2)
            payload["ranks"]["rank5"]={"source_id":"A","reviewed_frames":True,
                "frame_timestamps_sec":[0.2,2.1,4.4],
                "review_notes":"Observed five-second original dog motion and a weak visual payoff.",
                "points":{"visible_action":14,"comedic_surprise":12,
                          "setup_payoff_timing":10,"mobile_readability":12,"distinctness":5}}
            path.write_text(json.dumps(payload))
            scores,blockers=incumbent_reviews(profile,path)
            self.assertEqual(scores["rank5"],53)
            self.assertIsNone(scores["rank2"])
            self.assertEqual(blockers,["RANK2_NOT_VISUALLY_SCORED"])
            payload["ranks"]["rank5"]["points"]["comedic_surprise"]=99
            path.write_text(json.dumps(payload))
            scores,blockers=incumbent_reviews(profile,path)
            self.assertIsNone(scores["rank5"])
            self.assertIn("RANK5_SCORE_EVIDENCE_INVALID",blockers)

    def test_report_never_upgrades_unreviewed_candidate_even_when_baseline_scored(self):
        from dog_replacement_report import RUBRIC
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            profile={"shots":{"hook":{"source_id":"H","action":"bag"},
                "rank5":{"source_id":"A","action":"jump"},
                "rank4":{"source_id":"C","action":"shake"},
                "rank3":{"source_id":"D","action":"skate"},
                "rank2":{"source_id":"B","action":"catch"},
                "rank1":{"source_id":"F","action":"balance"},
                "outro":{"source_id":"F","action":"tug"}}}
            scored={"schema_version":1,"review_kind":"incumbent_rank_segment_scoring",
                "rubric_version":"dog_rank_segment_v1","publication_approved":False,
                "max_points":RUBRIC,"ranks":{
                    "rank5":{"source_id":"A","reviewed_frames":True,
                             "frame_timestamps_sec":[0,2,4],
                             "review_notes":"Exact source verified for weak five-second jump",
                             "points":{"visible_action":15,"comedic_surprise":12,
                                       "setup_payoff_timing":10,"mobile_readability":10,
                                       "distinctness":8}},
                    "rank2":{"source_id":"B","reviewed_frames":False,"points":None}}}
            candidate={"id":"PX-TEST","rank_target":"rank5",
                       "source_url":"https://www.pexels.com/video/test-123/",
                       "creator":"Source","license_url":"https://www.pexels.com/license/",
                       "sha256":"a"*64,"action_family":"toy_reaction",
                       "payoff_sec":2,"start_sec":0,"duration_sec":10,
                       "editorial_score":97,"reviewed_frames":False,
                       "semantic_review":"UNVERIFIED","rights_status":"UNVERIFIED"}
            p,a,s=[root/x for x in ("profile.json","audition.json","scores.json")]
            for file,data in ((p,profile),(a,{"candidates":[candidate]}),(s,scored)):
                file.write_text(json.dumps(data))
            result=report(p,a,incumbent_review_path=s)
            self.assertEqual(result["incumbent_review_scores"]["rank5"],55)
            self.assertTrue(all(x["status"]=="NO_UPGRADE" for x in result["decisions"]))
            self.assertFalse(result["publication_approved"])

    def test_actual_rank5_visual_78_is_blocked_by_rights_not_shortage(self):
        from dog_replacement_report import read_sample_reviewed_candidates
        root=Path(__file__).resolve().parents[1]
        reviewed=root/"sample/dog_rank5_reviewed_candidates_v1.json"
        incumbent=root/"sample/dog_incumbent_segment_review_v1.json"
        profile=root/"sample/dog_editorial_profile_v1.json"
        visual=read_sample_reviewed_candidates(reviewed)
        self.assertEqual(len(visual),1)
        self.assertEqual(visual[0]["editorial_score"],78)
        self.assertEqual(visual[0]["rights_status"],"UNVERIFIED")
        with tempfile.TemporaryDirectory() as tmp:
            empty=Path(tmp)/"old.json"
            empty.write_text(json.dumps({"candidates":[]}))
            result=report(profile,empty,incumbent_review_path=incumbent,
                          reviewed_candidate_path=reviewed)
        self.assertEqual(result["candidate_count"],1)
        self.assertEqual(result["incumbent_review_scores"],{"rank5":55,"rank2":72})
        self.assertEqual(result["visually_reviewed_candidate_ids_rights_pending"],
                         ["PX-5263686"])
        self.assertEqual(result["decisions"][0]["reason"],"RIGHTS_REVIEW_REQUIRED")
        self.assertEqual(result["decisions"][0]["source_id"],"PX-9006741")
        self.assertEqual(result["decisions"][1]["reason"],"EDITORIAL_SOURCE_SHORTAGE")
        self.assertEqual(result["next_action"],"RIGHTS_REVIEW_REQUIRED_FOR_RANK5")
        self.assertFalse(result["publication_approved"])
        self.assertIsNone(result["editorial_score"])

    def test_tampered_rank5_manifest_rejected_instead_of_approving(self):
        from dog_replacement_report import read_sample_reviewed_candidates
        original=Path(__file__).resolve().parents[1]/"sample/dog_rank5_reviewed_candidates_v1.json"
        data=json.loads(original.read_text())
        for field,value in (("rights_status","CLEARED"),
                            ("editorial_score",99),
                            ("publication_approved",True),
                            ("sha256","a"*64)):
            copy=json.loads(json.dumps(data))
            copy["candidates"][0][field]=value
            with tempfile.TemporaryDirectory() as tmp:
                file=Path(tmp)/"tampered.json"
                file.write_text(json.dumps(copy))
                with self.subTest(field=field),self.assertRaises(ValueError):
                    read_sample_reviewed_candidates(file)

    def test_unreviewed_candidates_do_not_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = {"shots": {
                "hook": {"source_id": "A", "action": "jump"},
                "rank5": {"source_id": "B", "action": "leap"},
                "rank4": {"source_id": "C", "action": "shake"},
                "rank3": {"source_id": "D", "action": "skate"},
                "rank2": {"source_id": "E", "action": "catch"},
                "rank1": {"source_id": "F", "action": "balance"},
                "outro": {"source_id": "F", "action": "tug"}}}
            audition = {"candidates": [{"id": "G", "rank_target": "rank5",
                                        "disposition": "PASSED_OVER"}]}
            p, a = root/"profile.json", root/"audition.json"
            p.write_text(json.dumps(profile))
            a.write_text(json.dumps(audition))
            result = report(p, a)
            self.assertEqual(result["candidate_count"], 1)
            self.assertTrue(all(d["status"] == "NO_UPGRADE" for d in result["decisions"]))
            self.assertIsNone(result["editorial_score"])
            self.assertFalse(result["publication_approved"])


if __name__ == "__main__":
    unittest.main()
