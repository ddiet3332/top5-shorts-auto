#!/usr/bin/env python3
"""Automated *technical* QA, not a substitute for editorial/rights review."""
import argparse
import json
import subprocess
from pathlib import Path

def score(video, technical_path, manifest_path):
    video=Path(video)
    technical=json.loads(Path(technical_path).read_text(encoding="utf-8"))
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    checks={}
    checks["mp4_exists"]=video.is_file() and video.stat().st_size>100000
    checks["full_decode"]=technical.get("full_decode") is True
    checks["format_1080x1920_h264_aac"]=False
    checks["duration_30s"]=False
    checks["five_rank_sources"]=False
    checks["distinct_source_pages"]=False
    if checks["mp4_exists"]:
        info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(video)],text=True))
        v=[s for s in info["streams"] if s.get("codec_type")=="video"]
        a=[s for s in info["streams"] if s.get("codec_type")=="audio"]
        checks["format_1080x1920_h264_aac"]=len(v)==1 and len(a)==1 and v[0].get("codec_name")=="h264" and a[0].get("codec_name")=="aac" and (v[0].get("width"),v[0].get("height"))==(1080,1920)
        checks["duration_30s"]=29.9<=float(info["format"]["duration"])<=30.2
    ranks=manifest.get("ranks",manifest.get("clips",[]))
    if isinstance(ranks,list):
        checks["five_rank_sources"]=len(ranks)==5
        pages=[x.get("source_page") for x in ranks if isinstance(x,dict)]
        checks["distinct_source_pages"]=len(pages)==5 and all(pages) and len(set(pages))==5
    weights={"mp4_exists":10,"full_decode":30,"format_1080x1920_h264_aac":25,"duration_30s":15,"five_rank_sources":10,"distinct_source_pages":10}
    points=sum(weights[k] for k,v in checks.items() if v)
    return {"technical_score_100":points,"technical_checks":checks,"technical_pass":points==100,
            "editorial_score_100":None,"editorial_review_verified":False,
            "rights_independently_cleared":False,"publication_approved":False,
            "warning":"Technical score is NOT the seven-category creative quality score; do not report as an 80+ editorial result."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--technical",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=score(a.video,a.technical,a.manifest)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
