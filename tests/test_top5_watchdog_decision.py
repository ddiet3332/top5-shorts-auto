import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_watchdog_decision import decide
from top5_watchdog_artifacts import WORKFLOWS, failure_reason, inspect
def run(state="completed",conclusion="failure",attempt=1,id=123,created="2026-11-16T00:00:00Z"):
    return dict(status=state,conclusion=conclusion,run_attempt=attempt,id=id,created_at=created)
class WatchdogTests(unittest.TestCase):
    def test_dependency_regression_is_classified_without_rerun(self):
        failing = {**run(),"html_url":"https://example.com/run"}
        jobs = {"jobs":[{"steps":[{"conclusion":"failure","name":"Run source and editorial safety regression tests"}]}]}
        with (patch.dict("os.environ", {"TOP5_DEFAULT_BRANCH":"main"}),
              patch("top5_watchdog_artifacts.api",side_effect=[
                  json.dumps({"workflow_runs":[failing]}),json.dumps(failing),
                  json.dumps({"artifacts":[]}),json.dumps(jobs)]) as api):
            self.assertIn("REGRESSION_OR_IMPORT_FAILED",inspect("v25.yml",WORKFLOWS["v25.yml"]))
            self.assertFalse(any("rerun" in str(call) for call in api.call_args_list))

    def test_timeout_and_success_have_distinct_codes(self):
        self.assertEqual(failure_reason(run(conclusion="timed_out")),"TIMED_OUT")
        self.assertEqual(failure_reason(run(conclusion="success")),"SUCCESS_REQUIRES_ARTIFACT_CHECK")
    def test_active_run_blocks_duplicate(self):
        self.assertEqual(decide([run("in_progress",None)])["action"],"wait")
    def test_three_retries_max(self):
        self.assertEqual(decide([run(attempt=4)])["reason"],"three_retries_exhausted")
    def test_retry_first_three(self):
        for attempt in (1,2,3):
            self.assertEqual(decide([run(attempt=attempt)])["action"],"rerun_failed_jobs")
    def test_success_requires_artifact_inspection(self):
        self.assertEqual(decide([run(conclusion="success")])["action"],"inspect_artifact")
    def test_no_history_fails_closed(self):
        self.assertEqual(decide([])["action"],"block")
    def test_cancelled_is_not_retried(self):
        self.assertEqual(decide([run(conclusion="cancelled")])["action"],"block")
    def test_latest_run_not_old_failed_run(self):
        old=run(id=1)
        new=run(conclusion="success",id=2,created="2026-11-17T00:00:00Z")
        self.assertEqual(decide([old,new])["run_id"],2)

    def test_inspector_reports_active_run_without_artifact_lookup(self):
        workflow = "top5-ai-topic-planner.yml"
        active = {**run("in_progress", None), "html_url": "https://example.com/run"}
        with (patch.dict("os.environ", {"TOP5_DEFAULT_BRANCH": "main"}),
              patch("top5_watchdog_artifacts.api", side_effect=[
                  json.dumps({"workflow_runs": [active]}), json.dumps(active)]) as api):
            self.assertIn("진행 중", inspect(workflow, WORKFLOWS[workflow]))
            self.assertEqual(api.call_count, 2)

    def test_inspector_skips_expired_and_previous_attempt_artifacts(self):
        workflow = "top5-ai-topic-planner.yml"
        failed = {**run(attempt=4), "html_url": "https://example.com/run"}
        old = {"name": "top5-topic-plan-PM-3", "expired": False}
        expired = {"name": "top5-topic-plan-PM-4", "expired": True}
        with (patch.dict("os.environ", {"TOP5_DEFAULT_BRANCH": "main"}),
              patch("top5_watchdog_artifacts.api", side_effect=[
                  json.dumps({"workflow_runs": [failed]}), json.dumps(failed),
                  json.dumps({"artifacts": [old, expired]})]) as api):
            self.assertIn("three_retries_exhausted", inspect(workflow, WORKFLOWS[workflow]))
            self.assertEqual(api.call_count, 3)
if __name__=="__main__":
    unittest.main()
