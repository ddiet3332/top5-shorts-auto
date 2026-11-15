#!/usr/bin/env python3
"""Public pointer to latest V25 technical review-only 30-second MP4."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def make_index(qa,rights,*,repo,run_id,run_number,result):
    if not repo or "/" not in repo or run_id<1 or run_number<1:
        raise ValueError("GitHub run metadata required")
    qa=qa if isinstance(qa,dict) else {}
    rights=rights if isinstance(rights,dict) else {}
    valid=(result=="success"
           and qa.get("status")=="TECHNICAL_QA_PASSED_HUMOR_RIGHTS_UNVERIFIED"
           and qa.get("actual_full_video_audio_decode")=="PASS")
    return {
        "schema_version":1,
        "repo":repo,
        "run_id":run_id,"run_number":run_number,
        "workflow_status":result,
        "video_qa_status":"TECHNICAL_OK_REVIEW_ONLY" if valid else "FAILED_OR_NOT_VERIFIED",
        "video_filename":qa.get("file") if valid else None,
        "video_duration_sec":qa.get("video_duration_sec") if valid else None,
        "audio_duration_sec":qa.get("audio_duration_sec") if valid else None,
        "video_resolution":("1080x1920" if valid else None),
        "source_ids":qa.get("ranking_source_ids",[]) if valid else [],
        "artifact_name":f"TOP5-v25-video-{run_number}",
        "artifact_page":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
        "rights_gate":"UNVERIFIED",
        "rights_detail":rights.get("license_check","NOT_PROVEN"),
        "subjective_100_point_score":None,
        "approved_for_publication":False,
        "note":"Video file may be present, but rights, humor and YouTube monetization were not approved."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--qa",default="output/V25_TECHNICAL_QA.json")
    p.add_argument("--rights",default="output/V12_MIXED_RIGHTS_AUDIT.json")
    p.add_argument("--review",default="review")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",required=True,type=int)
    p.add_argument("--run-number",required=True,type=int)
    p.add_argument("--result",required=True)
    args=p.parse_args()
    def openjson(path):
        f=Path(path)
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    item=make_index(openjson(args.qa),openjson(args.rights),
                    repo=args.repo,run_id=args.run_id,
                    run_number=args.run_number,result=args.result)
    dest=Path(args.review);dest.mkdir(parents=True,exist_ok=True)
    latest=dest/"v25_video_latest.json"
    if latest.exists() and int(json.loads(latest.read_text(encoding="utf-8")).get("run_number",0))>=args.run_number:
        print("Skipping old V25 run");return
    data=json.dumps(item,ensure_ascii=False,indent=2)+"\n"
    latest.write_text(data,encoding="utf-8")
    history=dest/"v25_video_runs";history.mkdir(exist_ok=True)
    (history/f"{args.run_id}.json").write_text(data,encoding="utf-8")
    print("V25 indexed",args.run_number,item["video_qa_status"])


if __name__=="__main__":
    main()
