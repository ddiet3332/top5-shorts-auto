#!/usr/bin/env python3
"""Index latest V26 caption-only free-license finished review master."""
import argparse,json
from pathlib import Path

def make_index(qa,*,repo,run_id,run_number,result):
    qa=qa or {}
    okay=(result=="success" and isinstance(qa,dict)
          and qa.get("status")=="V26_REAL_30S_AV_DECODE_PASSED_NO_MONETIZATION_APPROVAL"
          and qa.get("soundtrack_same_original_synth_aac") is True
          and qa.get("duration")==30.0)
    return {
        "version":"V26_FREE",
        "run_id":run_id,"run_number":run_number,"build_result":result,
        "video_qa_verified":bool(okay),
        "repo":repo,
        "artifact_name":f"TOP5-v26-free-{run_number}",
        "artifact_url":f"https://github.com/{repo}/actions/runs/{run_id}#artifacts",
        "video_filename":qa.get("video_file") if okay else None,
        "source_count":5 if okay else 0,
        "creative_originality_improved":bool(okay),
        "editorial_100_point_score":None,
        "paid_stock_used":False,
        "narration":False,
        "free_source_license_page_evidence":"Pexels 3, CC0 1, CC BY 3.0 1; see review/V26_FREE_LICENSE_UPLOAD_README.md",
        "third_party_copyright_independently_verified":False,
        "youtube_monetization_approved":False,
        "auto_publication_approved":False
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--qa",default="output/v26_free_editorial_work/V26_FREE_TECHNICAL_QA.json")
    p.add_argument("--repo",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--run-number",type=int,required=True)
    p.add_argument("--result",required=True)
    p.add_argument("--review",default="review")
    a=p.parse_args()
    path=Path(a.qa)
    qa=json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    index=make_index(qa,repo=a.repo,run_id=a.run_id,run_number=a.run_number,result=a.result)
    out=Path(a.review);out.mkdir(exist_ok=True,parents=True)
    latest=out/"v26_free_latest.json"
    if latest.exists():
        previous=json.loads(latest.read_text(encoding="utf-8"))
        if previous.get("run_number",0)>=a.run_number:
            return
    data=json.dumps(index,ensure_ascii=False,indent=2)+"\n"
    latest.write_text(data,encoding="utf-8")
    runs=out/"v26_free_runs";runs.mkdir(exist_ok=True)
    (runs/f"{a.run_id}.json").write_text(data,encoding="utf-8")
    print("V26 free video run indexed:",index["run_number"],index["video_qa_verified"])
if __name__=="__main__":main()
