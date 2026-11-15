#!/usr/bin/env python3
"""Public tiny V26 rights-pipeline artifact pointer. Never approves publication."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def make_index(audit,*,repo,run_id,run_number,build_result):
    audit=audit if isinstance(audit,dict) else {}
    if not repo or "/" not in repo or run_id<1 or run_number<1:
        raise ValueError("Valid repository and run metadata required")
    return {
        "schema_version":1,
        "version":"V26",
        "repo":repo,
        "run_id":run_id,
        "run_number":run_number,
        "build_result":build_result,
        "baseline_version":audit.get("baseline_version","V25"),
        "baseline_score":audit.get("baseline_score",82),
        "candidate_pages":audit.get("candidate_count",0),
        "licensed_cats_ready_for_edit":0,
        "actual_footage_previewed":0,
        "actual_comedic_payoff_verified":0,
        "video_created":False,
        "V26_full_100point_score":None,
        "artifact_name":f"TOP5-v26-rights-{run_number}",
        "artifact_url":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
        "license_quote_requested":False,
        "license_payment_authorized":False,
        "youtube_monetization_approved":False,
        "publication_approved":False,
        "note":"Provider descriptions only. Full paid contract, owner/audio rights and original-source frame QA required before creating or sharing 30s V26."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audit",default="output/V26_RIGHTS_AND_HUMOR_TRIAGE.json")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--run-number",type=int,required=True)
    p.add_argument("--build-result",required=True)
    p.add_argument("--review-dir",default="review")
    a=p.parse_args()
    f=Path(a.audit)
    report=json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    index=make_index(report,repo=a.repo,run_id=a.run_id,
                     run_number=a.run_number,build_result=a.build_result)
    target=Path(a.review_dir);target.mkdir(exist_ok=True,parents=True)
    latest=target/"v26_latest.json"
    if latest.exists():
        old=json.loads(latest.read_text(encoding="utf-8"))
        if old.get("run_number",0)>=a.run_number:
            print("Skip outdated V26 summary");return
    serial=json.dumps(index,ensure_ascii=False,indent=2)+"\n"
    latest.write_text(serial,encoding="utf-8")
    history=target/"v26_runs";history.mkdir(exist_ok=True)
    (history/f"{a.run_id}.json").write_text(serial,encoding="utf-8")
    print("V26 indexed",a.run_id,"candidate pages:",index["candidate_pages"],"licensed:",0)


if __name__=="__main__":
    main()
