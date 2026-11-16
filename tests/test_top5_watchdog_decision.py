import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_watchdog_decision import decide
def run(state="completed",conclusion="failure",attempt=1,id=123,created="2026-11-16T00:00:00Z"):
    return dict(status=state,conclusion=conclusion,run_attempt=attempt,id=id,created_at=created)
class WatchdogTests(unittest.TestCase):
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
if __name__=="__main__":
    unittest.main()
