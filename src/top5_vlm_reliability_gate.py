#!/usr/bin/env python3
"""Deterministic hallucination/quality veto on the V38-generated *text*.

No text-only method verifies video truth. These flags are rejection triggers
only, NEVER proof of a correct observation or publishable caption.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def repeated_clause_ratio(text):
    """Repeated five-word phrases indicate degenerate generative decoding."""
    words=re.findall(r"[a-z]+",str(text).lower())
    if len(words)<16:return 0.
    spans=[" ".join(words[i:i+5]) for i in range(len(words)-4)]
    distribution=Counter(spans)
    repeats=sum(v-1 for v in distribution.values() if v>1)
    return round(repeats/max(1,len(spans)),3)


def reliability_rejections(description, source_title, motion):
    s=" ".join(str(description).split())
    lower=s.casefold()
    flags=[]
    if not s or len(s)<28:
        flags.append("DESCRIPTION_TOO_SHORT")
    if repeated_clause_ratio(s)>=.22:
        flags.append("DEGENERATE_REPEATED_PHRASES")
    if len(s)>200 and not re.search(r"[.!?]['\"\s]*$",s):
        flags.append("POSSIBLE_MODEL_TOKEN_TRUNCATION")
    if any(p in lower for p in ("first video","second video","third video")):
        flags.append("CHRONOLOGICAL_FRAMES_CONFUSED_FOR_SEPARATE_VIDEOS")
    if re.search(r"(?i)\b(?:the text|words on|number on|says|reads|the time)\b",s):
        # The rank footage has text overlays, but recognizing exact on-screen
        # content is neither action evidence nor a safe thumbnail fact.
        flags.append("UNVERIFIED_TEXT_OR_OCR_CLAIM")
    if re.search(r"[가-힣]",s):
        flags.append("GENERATED_KOREAN_WORDS_NOT_PROVEN_BY_VISUAL_QA")
    title=str(source_title).casefold()
    if ("domino" in title or "domino cu" in title) and "domino" not in lower:
        flags.append("FILENAME_EVENT_NOT_DESCRIBED_RECHECK")
    if ("chain reaction" in title or "rube goldberg" in title) and not any(
        w in lower for w in ("chain","machine","mechanism","ball","device")):
        flags.append("MECHANISM_NOT_IDENTIFIED_RECHECK")
    if "nearly static" in lower and (
        max(motion.get("adjacent_gray_change") or [0])>=18):
        flags.append("MODEL_STATIC_CLAIM_CONFLICTS_WITH_FRAME_CHANGES")
    # No 'pass' flag is ever provided. Absence of flags is not factual proof.
    return list(dict.fromkeys(flags))


def evaluate_generated_report(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("publication_approved") is not False or
        data.get("score_100") is not None or
        data.get("korean_caption_ready") is not False or
        not isinstance(data.get("rows"),list) or not data["rows"] or
        len(data["rows"])>5):
        raise ValueError("UNTRUSTED_OR_INVALID_VLM_REPORT")
    rows=[]
    for row in data["rows"]:
        if (row.get("publication_approved") is not False or
            row.get("real_action_verified") is not False or
            not isinstance(row.get("source_sha256"),str) or
            len(row["source_sha256"])!=64 or
            not isinstance(row.get("generated_visual_description_en"),str)):
            raise ValueError("VLM_RANK_NO_PUBLISH_OR_SHA_INVALID")
        flags=reliability_rejections(
            row["generated_visual_description_en"],
            row.get("source_title_for_human_review",""),
            row.get("relative_frame_change",{}))
        rows.append({
            "rank":row["rank"],
            "source_sha256":row["source_sha256"],
            "reliability_flags":flags,
            "specific_model_text_unreliable":bool(flags),
            "generated_text_is_verified_observation":False,
            "eligible_for_direct_korean_caption":False,
            "action_or_payoff_verified":False,
            "publication_approved":False,
        })
    report={
        "schema_version":1,
        "input_video_sha256":data["rendered_video_sha256"],
        "chosen_topic":data["chosen_topic"],
        "model":data["model"],
        "rank_count":len(rows),
        "ranks_with_explicit_model_red_flags":sum(bool(r["reliability_flags"]) for r in rows),
        "rows":rows,
        "score_100":None,
        "rights_independently_verified":False,
        "automatic_caption_generation_approved":False,
        "publication_approved":False,
        "status":"VLM_TEXT_IS_UNVERIFIED_CANDIDATE_NOT_PUBLICATION",
        "warning":"Zero flags is not a true-video-fact check. All model descriptions still require full-frame/source scrutiny."
    }
    return report


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    res=evaluate_generated_report(args.input)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"rank_count":res["rank_count"],
                      "ranks_with_explicit_model_red_flags":
                          res["ranks_with_explicit_model_red_flags"],
                      "publication_approved":False}))

if __name__=="__main__":
    main()
