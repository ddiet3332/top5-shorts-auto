#!/usr/bin/env python3
"""Public tiny V20 run pointer, never raw Commons videos or rights approvals."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def build_index(previews, rights, *, repo, run_id, run_number, result):
    if not repo or "/" not in repo or run_id < 1 or run_number < 1:
        raise ValueError("Valid GitHub run metadata required")
    previews=previews if isinstance(previews,dict) else {}
    rights=rights if isinstance(rights,dict) else {}
    approved_pages={x["title"]:x for x in rights.get("sources",[])
                    if isinstance(x,dict) and x.get("title")}
    rows=[]
    for c in previews.get("candidates",[]):
        if not isinstance(c,dict) or c.get("title") not in approved_pages:
            continue
        p=approved_pages[c["title"]]
        moments=[{"start_sec":float(x["start_sec"]),
                  "preview_duration_sec":float(x.get("preview_duration_sec",5))}
                 for x in c.get("moments",[])[:3] if isinstance(x,dict)
                 and isinstance(x.get("start_sec"),(int,float))]
        rows.append({
            "title":c["title"],"source_page":p["source_page"],
            "creator":p.get("author_metadata",""),
            "license_name":p.get("license_metadata",""),
            "license_url":p.get("license_url",""),
            "duration_sec":c.get("duration_sec"),
            "width":c.get("width"),"height":c.get("height"),
            "moments":moments,
            "content_humor_verified":False,
            "individual_rights_independently_verified":False,
            "publication_approved":False,
        })
    return {
        "schema_version":1,
        "repo":repo,"run_id":run_id,"run_number":run_number,
        "build_result":result,
        "artifact_name":f"TOP5-v20-review-{run_number}",
        "artifact_url":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
        "self_publication_metadata_pass_count":rights.get("current_metadata_pass_count",0),
        "preview_original_count":len(rows),
        "preview_file_count":sum(len(x["moments"]) for x in rows),
        "final_five_selected":0,
        "approved_for_publication":False,
        "candidates":rows,
        "note":"Self-published CC metadata and observed movement are not human comedy QA or monetization approval."
    }


def save_latest(result, folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    latest=folder/"v20_latest.json"
    if latest.exists():
        old=json.loads(latest.read_text(encoding="utf-8"))
        if int(old.get("run_number",0))>=result["run_number"]:
            return False
    contents=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    latest.write_text(contents,encoding="utf-8")
    history=folder/"v20_runs"
    history.mkdir(exist_ok=True)
    (history/f"{result['run_id']}.json").write_text(contents,encoding="utf-8")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",required=True,type=int)
    p.add_argument("--run-number",required=True,type=int)
    p.add_argument("--result",default="unknown")
    p.add_argument("--review-dir",default="review")
    args=p.parse_args()
    base=Path(args.output)
    def read(name):
        f=base/name
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    index=build_index(read("V20_CREATOR_PREVIEW_REPORT.json"),
                      read("V20_CREATOR_LICENSE_AUDIT.json"),
                      repo=args.repo,run_id=args.run_id,
                      run_number=args.run_number,result=args.result)
    changed=save_latest(index,args.review_dir)
    print("V20 run indexed" if changed else "V20 older/equal run skipped",
          index["run_number"],"reviewed original previews:",index["preview_original_count"])


if __name__=="__main__":
    main()
