#!/usr/bin/env python3
"""Fail-closed quality and rights decision for review-only TOP5 artifacts.

Never derives creative quality from technical decode, metadata or motion proxies.
No upload or publication capability.
"""
import argparse
import json
import hashlib
from pathlib import Path

CATEGORIES = {"hook":20,"fun_reversal":25,"ranking":15,"flow":15,
              "original_captions":10,"sound":10,"rights_monetization":5}

def evaluate(qa, rights, video_path=None):
    scores=qa.get("editorial_scores")
    valid=(isinstance(scores,dict) and set(scores)==set(CATEGORIES)
           and all(type(scores[k]) in (int,float) and 0<=scores[k]<=v
                   for k,v in CATEGORIES.items()))
    total=sum(scores.values()) if valid else None
    evidence=qa.get("full_video_review_evidence")
    reviewed=bool(isinstance(evidence,dict) and evidence.get("reviewed") is True
                  and isinstance(evidence.get("video_sha256"),str)
                  and len(evidence["video_sha256"])==64
                  and all(ch in "0123456789abcdef" for ch in evidence["video_sha256"].lower())
                  and evidence.get("reviewer")
                  and evidence.get("reviewed_at"))
    file_hash_ok=True
    if video_path is not None:
        path=Path(video_path)
        if not path.is_file():
            file_hash_ok=False
        else:
            h=hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024*1024),b""):
                    h.update(chunk)
            file_hash_ok=(isinstance(evidence,dict)
                          and h.hexdigest().lower()==str(evidence.get("video_sha256","")).lower())
    reviewed=reviewed and file_hash_ok
    rights_ok=(rights.get("source_rights_independently_cleared") is True
               and rights.get("all_five_sources_verified") is True
               and rights.get("youtube_reused_content_reviewed") is True
               and isinstance(rights.get("source_evidence"),list)
               and len(rights["source_evidence"])==5
               and len({x.get("source_page") for x in rights["source_evidence"] if isinstance(x,dict)})==5
               and all(isinstance(x,dict) and x.get("independent_review") is True
                       and x.get("license_evidence_url") and x.get("creator")
                       for x in rights["source_evidence"]))
    report={
        "score":total if reviewed else None,
        "score_verified":valid and reviewed,
        "report_80":bool(valid and reviewed and total>=80),
        "publication_candidate_85":bool(valid and reviewed and total>=85 and rights_ok),
        "rights_gate_passed":rights_ok,
        "youtube_upload_permitted":False,
        "reasons":[]
    }
    if not valid or not reviewed:
        report["reasons"].append("Full-video editorial scoring evidence incomplete")
    if not rights_ok:
        report["reasons"].append("Independent source rights and YouTube reused-content review incomplete")
    if report["report_80"] and not rights_ok:
        report["reasons"].append("80+ is review-only, NOT publication approval")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--qa",required=True)
    p.add_argument("--rights",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--video",required=True)
    a=p.parse_args()
    report=evaluate(json.loads(Path(a.qa).read_text()),
                    json.loads(Path(a.rights).read_text()),a.video)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
