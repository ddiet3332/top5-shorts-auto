#!/usr/bin/env python3
"""Evidence-based source-rights and TOP5 scoring automation; fail closed."""
import argparse, hashlib, json, subprocess
from pathlib import Path

WEIGHTS={"hook":20,"fun_reversal":25,"ranking":15,"flow":15,"original_captions":10,"sound":10,"rights_monetization":5}
def load(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError): return {}
def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()
def run(video,manifest,review,output):
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    m=load(manifest); evidence=load(review)
    clips=m.get("clips",[]) if isinstance(m.get("clips"),list) else []
    verified=[]
    for i,clip in enumerate(clips):
        src=str(clip.get("source_page") or "")
        record=next((x for x in evidence.get("sources",[]) if x.get("source_page")==src),{})
        required=("creator_verified","original_ownership_verified","commercial_use_permitted","license_terms_verified","third_party_rights_cleared")
        checks={key:record.get(key) is True for key in required}
        license_type=str(record.get("license") or clip.get("license") or "")
        attribution=record.get("attribution_provided") is True or license_type.upper() in ("CC0","PUBLIC DOMAIN")
        checks["attribution_compliant"]=attribution
        verified.append({"rank":clip.get("rank",5-i),"source_page":src or None,"license":license_type or None,
                         "creator":record.get("creator") or clip.get("author"),"evidence_url":record.get("evidence_url"),
                         "checks":checks,"approved":bool(src and record.get("evidence_url") and all(checks.values()))})
    unique=len({x["source_page"] for x in verified if x["source_page"]})==5
    all_rights=len(verified)==5 and unique and all(x["approved"] for x in verified)
    video=Path(video)
    technical={"exists":video.is_file(),"sha256":digest(video) if video.is_file() else None}
    if video.is_file():
        p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(video)],capture_output=True,text=True)
        try: technical["duration_seconds"]=round(float(json.loads(p.stdout)["format"]["duration"]),3)
        except (KeyError,ValueError,TypeError): technical["duration_seconds"]=None
        technical["duration_30s"]=technical["duration_seconds"] is not None and abs(technical["duration_seconds"]-30)<0.2
    scores=evidence.get("editorial_scores",{})
    score_valid=(isinstance(scores,dict) and set(scores)==set(WEIGHTS) and all(type(scores[k]) in (int,float) and 0<=scores[k]<=v for k,v in WEIGHTS.items()))
    reviewer=evidence.get("editorial_review",{})
    editorial_verified=bool(score_valid and reviewer.get("full_video_watched") is True and reviewer.get("reviewer") and reviewer.get("video_sha256")==technical["sha256"])
    score=sum(scores.values()) if editorial_verified else None
    ypp_review=evidence.get("youtube_reused_content_review",{})
    ypp_verified=ypp_review.get("substantive_original_value_verified") is True and bool(ypp_review.get("reviewer"))
    publish_candidate=bool(all_rights and editorial_verified and score>=85 and ypp_verified and technical.get("duration_30s"))
    result={"video":str(video),"technical":technical,"sources":verified,"five_unique_sources":unique,
            "rights_evidence_complete":all_rights,"editorial_score":score,"editorial_score_verified":editorial_verified,
            "youtube_reuse_evidence_complete":ypp_verified,"publication_candidate":publish_candidate,
            "youtube_monetization_guaranteed":False,"youtube_upload_permitted":False,
            "reasons":[k for k,v in {"five_independently_verified_sources":all_rights,"full_video_editorial_review":editorial_verified,
                "editorial_score_at_least_85":score is not None and score>=85,
                "youtube_reuse_review":ypp_verified,"30_second_video":technical.get("duration_30s",False)}.items() if not v]}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"publication_candidate":publish_candidate,"editorial_score":score,"reasons":result["reasons"]},ensure_ascii=False))
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for flag in ("video","manifest","review","output"):p.add_argument("--"+flag,required=True)
    a=p.parse_args();run(a.video,a.manifest,a.review,a.output)
