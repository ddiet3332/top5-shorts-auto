#!/usr/bin/env python3
"""Small public GitHub Actions pointer for the latest V19 source-diverse review.

No licensed/stock video or external download URL is committed to the repo.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any


def compact_index(audit: dict[str, Any] | None, *, repo: str,
                  run_id: int, run_number: int, result: str) -> dict[str, Any]:
    if not repo or "/" not in repo or run_id < 1 or run_number < 1:
        raise ValueError("Invalid GitHub run")
    rows = audit.get("candidates", []) if isinstance(audit, dict) else []
    if not isinstance(rows, list):
        rows = []
    compact=[]
    for x in rows[:15]:
        if not isinstance(x,dict):
            continue
        compact.append({
            "id":str(x.get("id",""))[:40],
            "provider":str(x.get("provider",""))[:30],
            "title":str(x.get("title",""))[:150],
            "page_url":str(x.get("page_url",""))[:700],
            "license_label":str(x.get("license_label",""))[:100],
            "video_preview_status":str(x.get("video_preview_status",""))[:80],
            "preview_count":len(x.get("preview_windows",[])) if isinstance(x.get("preview_windows",[]),list) else 0,
            "publication_approved":False
        })
    return {
        "schema_version":1,
        "repository":repo,
        "run_id":run_id,
        "run_number":run_number,
        "build_result":result,
        "review_status":"AWAITING_HUMAN_EDITORIAL_AND_RIGHTS_REVIEW"
                        if result=="success" and compact else "NO_VERIFIED_PREVIEW_RESULT",
        "artifact_name":f"TOP5-v19-review-{run_number}",
        "artifact_web_page":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
        "candidate_page_count":len(compact),
        "preview_file_count":sum(c["preview_count"] for c in compact),
        "all_rights_approved":False,
        "publication_approved":False,
        "candidates":compact,
        "notice":"Pexels, Mixkit, and Pixabay footage is not automatically CC. No auto-publishing."
    }


def publish_latest(item: dict, folder: Path) -> bool:
    folder.mkdir(parents=True,exist_ok=True)
    latest=folder/"v19_latest.json"
    if latest.exists():
        current=json.loads(latest.read_text(encoding="utf-8"))
        if int(current.get("run_number",0)) >= item["run_number"]:
            print("Skipping older/equal V19 run index")
            return False
    payload=json.dumps(item,ensure_ascii=False,indent=2)+"\n"
    latest.write_text(payload,encoding="utf-8")
    history=folder/"v19_runs"
    history.mkdir(exist_ok=True)
    (history/f"{item['run_id']}.json").write_text(payload,encoding="utf-8")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audit",default="output/V19_SOURCE_DIVERSE_AUDIT.json")
    p.add_argument("--review-dir",default="review")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",required=True,type=int)
    p.add_argument("--run-number",required=True,type=int)
    p.add_argument("--result",default="unknown")
    args=p.parse_args()
    source=Path(args.audit)
    audit=json.loads(source.read_text(encoding="utf-8")) if source.exists() else None
    item=compact_index(audit,repo=args.repo,run_id=args.run_id,
                       run_number=args.run_number,result=args.result)
    updated=publish_latest(item,Path(args.review_dir))
    print("V19 index", "written" if updated else "unchanged",
          "run",item["run_number"],"previews",item["preview_file_count"])

if __name__=="__main__":
    main()
