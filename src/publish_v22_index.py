#!/usr/bin/env python3
"""V22 small public metadata pointer; review MP4s stay in Actions artifacts."""
import argparse,json
from pathlib import Path

def summary(audit,*,repo,run_id,run_number,build_result):
    audit=audit if isinstance(audit,dict) else {}
    rows=audit.get("candidates",[])
    if not isinstance(rows,list):
        rows=[]
    return {
      "schema_version":1,
      "repository":repo,"run_id":run_id,"run_number":run_number,
      "build_result":build_result,
      "artifact_name":f"TOP5-v22-audition-{run_number}",
      "artifact_page":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
      "candidate_pages":len(rows),
      "preview_originals":sum(x.get("preview_count",0)>0 for x in rows),
      "preview_windows":sum(x.get("preview_count",0) for x in rows),
      "candidates":[{
          "id":str(x.get("id","")),
          "title":str(x.get("title","")),
          "action_group":str(x.get("action_group","")),
          "page":str(x.get("original_page","")),
          "status":str(x.get("status","")),
          "preview_count":x.get("preview_count",0),
          "failure_code":x.get("failure_code")
      } for x in rows],
      "actual_funny_editorial_approval":False,
      "rights_verified":False,
      "youtube_monetization_cleared":False,
      "publication_approved":False
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audit",default="output/V22_NEW_SOURCE_AUDIT.json")
    p.add_argument("--dir",default="review")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--run-number",type=int,required=True)
    p.add_argument("--build-result",required=True)
    a=p.parse_args()
    source=Path(a.audit)
    audit=json.loads(source.read_text(encoding="utf-8")) if source.exists() else None
    result=summary(audit,repo=a.repo,run_id=a.run_id,run_number=a.run_number,
                   build_result=a.build_result)
    out=Path(a.dir);out.mkdir(parents=True,exist_ok=True)
    p=out/"v22_latest.json"
    if p.exists():
        previous=json.loads(p.read_text(encoding="utf-8"))
        if previous.get("run_number",0)>=a.run_number:
            print("V22 index already newer");return
    contents=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    p.write_text(contents,encoding="utf-8")
    history=out/"v22_runs";history.mkdir(parents=True,exist_ok=True)
    (history/f"{a.run_id}.json").write_text(contents,encoding="utf-8")
    print("V22 indexed",a.run_number,"preview windows",result["preview_windows"])

if __name__=="__main__":
    main()
