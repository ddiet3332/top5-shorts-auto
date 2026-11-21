#!/usr/bin/env python3
"""Evidence-bound 256M vs 500M VLM on the exact same real final MP4.

The text-only veto flags catch obvious failures, not video-to-text truth.
Even if the larger model has fewer flags, this comparator does not claim a
validated scene action or create captions, an 85/100 score, or rights clearance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from top5_smolvlm2_editorial import MODEL_ID, CHALLENGER_MODEL_ID
from top5_vlm_reliability_gate import reliability_rejections, repeated_clause_ratio

RANK_ORDER=(5,4,3,2,1)

def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _check_report(doc, expected_model):
    if (doc.get("model")!=expected_model or doc.get("publication_approved") is not False
        or doc.get("korean_caption_ready") is not False
        or doc.get("score_100") is not None
        or not isinstance(doc.get("rendered_video_sha256"),str)
        or len(doc["rendered_video_sha256"])!=64
        or [x.get("rank") for x in doc.get("rows",[])]!=list(RANK_ORDER)
        or doc.get("not_verified_observation") is not True):
        raise ValueError("INVALID_OR_UNTRUSTED_VIDEO_MODEL_REPORT")
    for row in doc["rows"]:
        if (row.get("real_action_verified") is not False
            or row.get("publication_approved") is not False
            or row.get("suggested_caption_ko") is not None
            or len(str(row.get("source_sha256","")))!=64
            or not str(row.get("source_url","")).startswith("https://")
            or len(row.get("rendered_frame_times",[]))!=3
            or not isinstance(row.get("generated_visual_description_en"),str)):
            raise ValueError("INVALID_RANK_OR_PROVENANCE")

def _inspect_row(row):
    desc=row["generated_visual_description_en"]
    flags=reliability_rejections(
        desc,row["source_title_for_human_review"],
        row["relative_frame_change"])
    return {
        "text":desc,
        "text_characters":len(desc),
        "repeated_five_word_ratio":repeated_clause_ratio(desc),
        "reliability_flags":flags,
        "obvious_model_text_failure_count":len(flags),
        "factually_verified":False,
    }

def compare(reference, challenger):
    old=_read(reference)
    new=_read(challenger)
    _check_report(old,MODEL_ID)
    _check_report(new,CHALLENGER_MODEL_ID)
    if (old["rendered_video_sha256"]!=new["rendered_video_sha256"] or
        old["chosen_topic"]!=new["chosen_topic"]):
        raise ValueError("CROSS_MODEL_MEDIA_OR_TOPIC_MISMATCH")
    rows=[]
    for a,b in zip(old["rows"],new["rows"],strict=True):
        if not all(a.get(k)==b.get(k) for k in (
                "rank","source_sha256","source_url",
                "source_title_for_human_review","rendered_frame_times")):
            raise ValueError("RANK_OR_ORIGINAL_SOURCE_MISMATCH")
        old_res,new_res=_inspect_row(a),_inspect_row(b)
        rows.append({
            "rank":a["rank"],
            "source_page":a["source_url"],
            "source_sha256":a["source_sha256"],
            "three_video_frame_times":a["rendered_frame_times"],
            "original_title":a["source_title_for_human_review"],
            "baseline_256m":old_res,
            "challenger_500m":new_res,
            "model_text_flags_reduced":len(new_res["reliability_flags"])<len(old_res["reliability_flags"]),
            "real_action_correctness_verified":False,
            "rank_payoff_verified":False,
            "korean_caption_approved":False,
        })
    old_bad=sum(bool(x["baseline_256m"]["reliability_flags"]) for x in rows)
    new_bad=sum(bool(x["challenger_500m"]["reliability_flags"]) for x in rows)
    result={
        "schema_version":1,
        "status":"EXACT_SAME_VIDEO_MODEL_BENCHMARK_EDITORIAL_REVIEW_ONLY",
        "topic":old["chosen_topic"],
        "video_sha256":old["rendered_video_sha256"],
        "same_original_sources_and_temporal_frames":True,
        "baseline_model":MODEL_ID,
        "challenger_model":CHALLENGER_MODEL_ID,
        "rank_count":5,
        "baseline_explicit_warning_ranks":old_bad,
        "challenger_explicit_warning_ranks":new_bad,
        "warning_ranks_delta":new_bad-old_bad,
        "lower_flag_count_is_not_video_accuracy":True,
        "upgrade_to_challenger_for_captions_approved":False,
        "actual_scene_action_verified":False,
        "editorial_score_100":None,
        "user_publishable_captions_created":False,
        "source_rights_verified":False,
        "youtube_monetization_verified":False,
        "manual_upload_only":True,
        "publication_approved":False,
        "rows":rows,
    }
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--challenger",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    rep=compare(args.baseline,args.challenger)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"V39_SAME_VIDEO_256M_VS_500M.json").write_text(
        json.dumps(rep,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# TOP5 actual same-video 256M versus 500M",
           "",
           f"Video sha256: `{rep['video_sha256']}`",
           f"Topic: `{rep['topic']}`",
           "",
           "| Rank | 256M quality flags | 500M quality flags |",
           "|---:|---|---|"]
    for row in rep["rows"]:
        old=", ".join(row["baseline_256m"]["reliability_flags"]) or "No explicit flags"
        new=", ".join(row["challenger_500m"]["reliability_flags"]) or "No explicit flags"
        lines.append(f"| {row['rank']} | {old} | {new} |")
    lines.extend(["",
        f"Explicit red-flag ranks: 256M {rep['baseline_explicit_warning_ranks']}/5; 500M {rep['challenger_explicit_warning_ranks']}/5.",
        "",
        "**CRITICAL:** Fewer textual anomaly flags is NOT proof the video description is correct.",
        "Every rank needs independent source-video verification, real original Korean creative caption,",
        "hook/payoff audit, per-source rights/YPP checks. Neither model is automatically approved.",
    ])
    (args.out/"V39_COMPARE_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"topic":rep["topic"],
                     "baseline_warn_ranks":rep["baseline_explicit_warning_ranks"],
                     "challenger_warn_ranks":rep["challenger_explicit_warning_ranks"],
                     "publication_approved":False},ensure_ascii=False))

if __name__=="__main__":main()
