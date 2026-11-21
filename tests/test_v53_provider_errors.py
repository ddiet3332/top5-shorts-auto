"""V53: distinguish Wikimedia throttling from true five-video inventory shortage."""
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_provider_failure_gate import (
    download_with_bounded_retry,provider_error_code)
from top5_topic_recovery import run_recovery,candidate_failure_diagnostics

def http_error(status,headers=None):
    return urllib.error.HTTPError(
        "https://upload.wikimedia.org/example.webm",status,
        "rate limited" if status==429 else "error",headers or {},None)

def audit_template():
    return {
        "requested_topic":"auto","topic":"cat_surprises",
        "status":"READY_FOR_DOWNLOAD_CHECK",
        "rights_verified":False,"publication_approved":False,
        "topic_standings":[
            {"topic_id":"cat_surprises","metadata_eligible":10,"heuristic_score":99},
            {"topic_id":"nature_moments","metadata_eligible":20,"heuristic_score":80}
        ]
    }

class ProviderRetryTests(unittest.TestCase):
    def test_http_429_retries_only_twice_with_bounded_delay(self):
        calls=[]
        sleeps=[]
        def downloader(source,dest):
            calls.append(source)
            if len(calls)<3:
                raise http_error(429)
            return 123456
        result=download_with_bounded_retry(
            downloader,{"title":"test"},"/no/network/called",
            sleeper=sleeps.append)
        self.assertEqual(result,123456)
        self.assertEqual(len(calls),3)
        self.assertEqual(sleeps,[2.0,5.0])

    def test_retry_after_is_bounded_at_twenty_seconds(self):
        delays=[]
        attempts=[0]
        def downloader(*_):
            attempts[0]+=1
            if attempts[0]==1:
                raise http_error(429,{"Retry-After":"4"})
            return 1
        self.assertEqual(download_with_bounded_retry(
            downloader,{},None,sleeper=delays.append),1)
        self.assertEqual(delays,[4.0])

    def test_permanent_403_and_404_are_not_temporarily_retried(self):
        for code in (403,404):
            self.assertIsNone(provider_error_code(http_error(code)))
            calls=[]
            def downloader(*_):
                calls.append(1)
                raise http_error(code)
            with self.assertRaises(urllib.error.HTTPError):
                download_with_bounded_retry(
                    downloader,{},None,
                    sleeper=lambda _sec:self.fail("403 or 404 slept"))
            self.assertEqual(len(calls),1)

    def test_transient_http_503_and_timeout_are_classified(self):
        self.assertEqual(provider_error_code(http_error(503)),"PROVIDER_HTTP_503")
        self.assertEqual(provider_error_code(TimeoutError()),"PROVIDER_NETWORK_UNAVAILABLE")
        self.assertIsNone(provider_error_code(ValueError("invalid MP4 bytes")))

    def test_real_inventory_0_of_5_with_provider_429_stops_topic_rotation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"DISCOVERY_AUDIT.json"
            path.write_text(json.dumps(audit_template()))
            seen=[]
            def runner(cmd,**_):
                topic=cmd[cmd.index("--topic")+1]
                seen.append(topic)
                folder=Path(cmd[cmd.index("--output")+1])
                folder.mkdir(parents=True,exist_ok=True)
                (folder/"V30_CANDIDATES.json").write_text(json.dumps([
                    {"title":f"File:A{i}.webm","status":"TEMPORARY_PROVIDER_ERROR",
                     "reason_code":"PROVIDER_HTTP_429",
                     "why":"HTTPError: HTTP Error 429: Too Many Requests"}
                    for i in range(3)],ensure_ascii=False))
                return SimpleNamespace(returncode=1,
                    stdout="CANDIDATE 1 TEMPORARY_PROVIDER_ERROR",
                    stderr="SourceShortage: SOURCE_SHORTAGE: 0/5")
            self.assertFalse(run_recovery(path,root,runner=runner))
            self.assertEqual(seen,["cat_surprises"])
            report=json.loads((root/"TOP5_TOPIC_RECOVERY_QA.json").read_text())
            self.assertEqual(report["status"],"PROVIDER_FAILURE_NOT_SOURCE_SHORTAGE")
            self.assertEqual(report["attempts"][0]["status"],
                             "TRANSIENT_PROVIDER_UNAVAILABLE")
            self.assertEqual(report["attempts"][0]["source_failure_diagnostics"][
                "temporary_provider_failures"],3)
            self.assertFalse(report["publication_approved"])
            self.assertFalse((root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4").exists())

    def test_zero_of_five_without_provider_evidence_remains_unverified_shortage(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            trial=root/"attempt"
            trial.mkdir()
            (trial/"V30_CANDIDATES.json").write_text(json.dumps([
                {"title":"File:Dark.webm","status":"REJECTED","why":"SOURCE_WINDOW_MOSTLY_DARK"}
            ]))
            result=candidate_failure_diagnostics(trial)
            self.assertEqual(result["temporary_provider_failures"],0)
            self.assertEqual(result["source_rejection_count"],1)
            self.assertEqual(result["candidate_attempt_count"],1)

if __name__=="__main__":
    unittest.main()
