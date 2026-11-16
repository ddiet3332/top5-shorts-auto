#!/usr/bin/env python3
"""Deterministic watchdog decision: no score fabrication and no upload."""
import json
import sys

def decide(runs):
    active=[r for r in runs if r.get("status") in ("queued","in_progress","waiting","requested")]
    if active:
        return {"action":"wait","reason":"active_run"}
    if not runs:
        return {"action":"block","reason":"no_history"}
    r=max(runs,key=lambda x:(x.get("created_at",""),int(x.get("id",0))))
    state=r.get("conclusion")
    raw_attempt=r.get("run_attempt")
    if raw_attempt is None:
        return {"action":"block","reason":"missing_run_attempt","run_id":r["id"]}
    try:
        attempt=int(raw_attempt)
    except (TypeError,ValueError):
        return {"action":"block","reason":"invalid_run_attempt","run_id":r["id"]}
    if attempt<1:
        return {"action":"block","reason":"invalid_run_attempt","run_id":r["id"]}
    if state=="success":
        return {"action":"inspect_artifact","run_id":r["id"]}
    if state not in ("failure","timed_out"):
        return {"action":"block","reason":"non_retryable_state","run_id":r["id"]}
    if attempt>=4:
        return {"action":"block","reason":"three_retries_exhausted","run_id":r["id"]}
    return {"action":"rerun_failed_jobs","run_id":r["id"],"next_attempt":attempt+1}

if __name__=="__main__":
    print(json.dumps(decide(json.load(sys.stdin)),sort_keys=True))
