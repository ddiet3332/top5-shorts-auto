"""Auto TOP5 subject recovery: never fill with unrelated footage or mask bugs."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from top5_topic_recovery import ordered_topics, run_recovery, verified_video


def report(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def inventory(initial="objects_oddities", requested="auto"):
    return {
        "requested_topic": requested, "topic": initial,
        "status": "READY_FOR_DOWNLOAD_CHECK",
        "rights_verified": False, "publication_approved": False,
        "topic_standings": [
            {"topic_id": "objects_oddities", "metadata_eligible": 16, "heuristic_score": 20.0},
            {"topic_id": "cat_surprises", "metadata_eligible": 7, "heuristic_score": 13.0},
            {"topic_id": "nature_moments", "metadata_eligible": 44, "heuristic_score": 99.0},
            {"topic_id": "human_moments", "metadata_eligible": 1, "heuristic_score": 5.0},
        ],
    }


def fake_probe(_):
    return {"format": {"duration": "30.000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080,
                 "height": 1920, "r_frame_rate": "24/1", "nb_frames": "720",
                 "duration": "30.000"},
                {"codec_type": "audio", "codec_name": "aac", "duration": "30.000"},
            ]}


def write_fake_render(folder, topic):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "TOP5_AUTO_V29_REVIEW_1080x1920.mp4").write_bytes(b"synthetic-evidence-not-real-media")
    report(folder / "TOPIC_RECOMMENDATIONS_V32.json", {"chosen_topic": topic})
    report(folder / "V32_TECHNICAL_QA.json", {
        "topic": topic, "full_decode": "PASS", "source_count": 5,
        "video_frames": 720, "exact_720_frames": True,
        "source_permissions_fully_cleared": False, "publication_approved": False})
    report(folder / "SELECTED_SOURCE_PROVENANCE.json", {
        "selected": [
            {"rank": 5-i, "sha256": f"{i+1:064x}",
             "rights_verified": False, "publication_approved": False}
            for i in range(5)],
        "rights_verified": False, "publication_approved": False})


class TopicRecoveryTests(unittest.TestCase):
    def test_resort_only_to_already_discovered_metadata_viable_topics(self):
        self.assertEqual(ordered_topics(inventory()), [
            "objects_oddities", "nature_moments", "cat_surprises"])
        self.assertEqual(ordered_topics(inventory(requested="objects_oddities")),
                         ["objects_oddities"])
        x=inventory(requested="objects_oddities")
        x["topic"]="nature_moments"
        with self.assertRaises(ValueError):
            ordered_topics(x)

    def test_real_objects_shortage_retries_nature_and_reports_actual_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit=root/"DISCOVERY_AUDIT.json"
            report(audit,inventory())
            calls=[]
            def runner(cmd, **_kw):
                topic=cmd[cmd.index("--topic")+1]
                calls.append(topic)
                if topic=="objects_oddities":
                    return SimpleNamespace(returncode=1,stdout="",
                        stderr="top5_hook_selection.SourceShortage: DISTINCT_OBJECT_EVENT_SHORTAGE: 4/5")
                write_fake_render(Path(cmd[cmd.index("--output")+1]),topic)
                return SimpleNamespace(returncode=0,stdout="V32 VIDEO COMPLETE",stderr="")
            self.assertTrue(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(calls,["objects_oddities","nature_moments"])
            final=json.loads(audit.read_text())
            self.assertEqual(final["topic"],"nature_moments")
            self.assertEqual(final["initial_topic"],"objects_oddities")
            self.assertEqual(final["status"],"RENDERED_AFTER_INVENTORY_RECOVERY")
            self.assertTrue((root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4").is_file())
            qa=json.loads((root/"TOP5_TOPIC_RECOVERY_QA.json").read_text())
            self.assertEqual(qa["chosen_render_topic"],"nature_moments")
            self.assertEqual(len(qa["attempts"]),2)
            self.assertIsNone(qa["editorial_score_100"])
            self.assertFalse(qa["publication_approved"])

    def test_explicit_objects_source_shortage_fails_not_subject_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit=root/"DISCOVERY_AUDIT.json"
            report(audit,inventory(requested="objects_oddities"))
            calls=[]
            def runner(cmd, **kw):
                calls.append(cmd[cmd.index("--topic")+1])
                return SimpleNamespace(returncode=1,stdout="DISTINCT_OBJECT_EVENT_SHORTAGE",stderr="")
            self.assertFalse(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(calls,["objects_oddities"])
            self.assertFalse((root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4").exists())

    def test_non_source_renderer_failure_does_not_trigger_alternate_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit=root/"DISCOVERY_AUDIT.json"
            report(audit,inventory())
            calls=[]
            def runner(cmd, **kw):
                calls.append(cmd)
                return SimpleNamespace(returncode=1,stdout="",stderr="RuntimeError: FFmpeg encoder broken")
            self.assertFalse(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(len(calls),1)
            qa=json.loads((root/"TOP5_TOPIC_RECOVERY_QA.json").read_text())
            self.assertEqual(qa["status"],"NON_SOURCE_RENDER_FAILURE_FATAL")

    def test_invalid_success_evidence_cannot_be_rescued_by_topic_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit=root/"DISCOVERY_AUDIT.json"
            report(audit,inventory())
            calls=[]
            def runner(cmd, **kw):
                calls.append(cmd)
                folder=Path(cmd[cmd.index("--output")+1])
                write_fake_render(folder,cmd[cmd.index("--topic")+1])
                info=json.loads((folder/"V32_TECHNICAL_QA.json").read_text())
                info["video_frames"]=717
                report(folder/"V32_TECHNICAL_QA.json",info)
                return SimpleNamespace(returncode=0,stdout="COMPLETE",stderr="")
            self.assertFalse(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(len(calls),1)
            self.assertFalse((root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4").exists())

    def test_a_second_source_shortage_can_try_third_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);audit=root/"DISCOVERY_AUDIT.json"
            report(audit,inventory())
            seen=[]
            def runner(cmd, **kw):
                topic=cmd[cmd.index("--topic")+1];seen.append(topic)
                if len(seen)<3:
                    return SimpleNamespace(returncode=2,stdout="SOURCE_SHORTAGE",stderr="")
                write_fake_render(Path(cmd[cmd.index("--output")+1]),topic)
                return SimpleNamespace(returncode=0,stdout="",stderr="")
            self.assertTrue(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(seen,["objects_oddities","nature_moments","cat_surprises"])

    def test_no_eligible_fallback_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);audit=root/"DISCOVERY_AUDIT.json"
            i=inventory()
            i["topic_standings"]=[{"topic_id":"objects_oddities","metadata_eligible":16}]
            report(audit,i)
            def runner(*_args, **_kwargs):
                return SimpleNamespace(returncode=2,stdout="DISTINCT_OBJECT_EVENT_SHORTAGE",stderr="")
            self.assertFalse(run_recovery(audit,root,runner=runner,probe=fake_probe))
            self.assertEqual(json.loads((root/"TOP5_TOPIC_RECOVERY_QA.json").read_text())["status"],
                             "NO_FIVE_DISTINCT_SOURCE_TOPIC_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
