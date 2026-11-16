#!/usr/bin/env python3
"""Plan bounded editorial repairs from verified clip-level reviews.

This does NOT claim to understand video, acquire rights, or render MP4.
It only chooses independently reviewed replacement clips; no upload.
"""
import argparse
import json
from pathlib import Path

def plan(review, candidates, previous_attempts=0, max_repairs=3):
    if type(previous_attempts) is not int or previous_attempts<0:
        raise ValueError("invalid previous_attempts")
    if previous_attempts>=max_repairs:
        return {"status":"STOP","reason":"repair_limit_reached","repairs":[]}
    clips=review.get("clips",[])
    if len(clips)!=5 or len({c.get("rank") for c in clips})!=5:
        return {"status":"BLOCKED","reason":"five_rank_reviews_required","repairs":[]}
    unknown=[c for c in clips if c.get("verified") is not True
             or type(c.get("editorial_score")) not in (int,float)
             or not 0<=c["editorial_score"]<=100
             or type(c.get("minimum_score",70)) not in (int,float)]
    if unknown:
        return {"status":"BLOCKED","reason":"unreviewed_or_invalid_clip_scores","repairs":[]}
    bad=[c for c in clips if c["editorial_score"]<c.get("minimum_score",70)]
    if not bad:
        return {"status":"NO_CHANGE","reason":"no_verified_weak_clips","repairs":[]}
    used={c.get("source_page") for c in clips}
    replacements=[]
    for weak in sorted(bad,key=lambda c:c["editorial_score"]):
        options=[x for x in candidates if x.get("source_page") not in used
                 and x.get("editorial_reviewed") is True
                 and x.get("rights_independently_cleared") is True
                 and x.get("creator") and x.get("license_evidence_url")
                 and type(x.get("editorial_score")) in (int,float)
                 and 0<=x["editorial_score"]<=100
                 and x["editorial_score"]>weak["editorial_score"]]
        if not options:
            return {"status":"BLOCKED","reason":"no_rights_cleared_better_replacement",
                    "weak_rank":weak["rank"],"repairs":[]}
        best=max(options,key=lambda x:x["editorial_score"])
        used.add(best["source_page"])
        replacements.append({"rank":weak["rank"],"from":weak.get("source_page"),
                             "to":best["source_page"],"expected_gain":best["editorial_score"]-weak["editorial_score"]})
    return {"status":"READY_FOR_REBUILD","attempt":previous_attempts+1,
            "repairs":replacements,"publication_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--review",required=True)
    p.add_argument("--candidates",required=True)
    p.add_argument("--attempt",type=int,default=0)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=plan(json.loads(Path(a.review).read_text()),
                json.loads(Path(a.candidates).read_text()),a.attempt)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
