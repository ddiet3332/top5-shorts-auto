#!/usr/bin/env python3
"""Source-hash-bound real-frame editorial evidence for DEFAULT automatic TOP5.

The ordinary topic-to-MP4 workflow lacked the 35-frame audit already used by
four-category technical trials. Do not score humor, license rights or publish.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from top5_scene_evidence import (VIDEO,V32_WINDOWS,read,sha256,
    sample_times,capture,luminance_median,possible_repeated_subject,
    REVIEW_PLACEHOLDERS)

TOPICS={"cat_surprises","dog_surprises","human_moments",
        "objects_oddities","nature_moments"}


def source_plan(root):
    root=Path(root)
    topic=read(root/"TOPIC_RECOMMENDATIONS_V32.json")["chosen_topic"]
    if topic not in TOPICS:
        raise ValueError("TOPIC_MUST_MATCH_ACTUAL_RENDER")
    qa=read(root/"V32_TECHNICAL_QA.json")
    if (qa.get("topic")!=topic or qa.get("full_decode")!="PASS" or
        qa.get("publication_approved") is not False or
        qa.get("source_count")!=5):
        raise ValueError("INVALID_TECHNICAL_RENDER_EVIDENCE")
    provenance=read(root/"SELECTED_SOURCE_PROVENANCE.json")
    titles=read(root/"SOURCE_SELECTION_REVIEW.json")["items_in_rank_5_to_1_order"]
    ranks=read(root/"V30_CREATIVE_AND_RIGHTS_GATES.json")["rank_5_to_1"]
    originals=provenance["selected"]
    if len(originals)!=5 or len(titles)!=5 or len(ranks)!=5:
        raise ValueError("NOT_FIVE_RANKS")
    expected=[5,4,3,2,1]
    if ([r["rank"] for r in originals]!=expected or
        [r["rank"] for r in ranks]!=expected or
        len({r["sha256"] for r in originals})!=5 or
        not all(len(str(r["sha256"]))==64 and
                str(r["source_page"]).startswith("https://") for r in originals) or
        provenance.get("publication_approved") is not False):
        raise ValueError("RANK_PROVENANCE_MISMATCH")
    rows=[]
    for i,((rank,start,end),source,named,creative) in enumerate(
        zip(V32_WINDOWS,originals,titles,ranks,strict=True)):
        if named["title"]!=creative["title"] or named["source_page"]!=source["source_page"]:
            raise ValueError("RANK_SOURCE_TITLE_AND_URL_MISMATCH")
        rows.append({
            "rank":rank, "start":start,"end":end,
            "source_sha256":source["sha256"],
            "source_url":source["source_page"],
            "title":named["title"],
            "caption":creative["caption"],
            "editorial_score":None,
            "action_verified":False,
        })
    return topic,rows


def evaluate_standard(root,*,capture_frame=capture):
    root=Path(root)
    video=root/VIDEO
    topic,rows=source_plan(root)
    if not video.is_file():
        raise ValueError("NO_ACTUAL_EDITED_MP4")
    digest=sha256(video)
    font=ImageFont.load_default()
    out_image=Image.new("RGB",(176*7,(315+24)*5),(238,238,238))
    pen=ImageDraw.Draw(out_image)
    findings=[]
    for index,row in enumerate(rows):
        frames=[]
        for j,t in enumerate(sample_times(row["start"],row["end"])):
            frame=capture_frame(video,t)
            if frame.size!=(360,640):
                raise ValueError("RENDERED_VIDEO_FRAME_NOT_9X16")
            frames.append({"second":t,"subject_region_median":luminance_median(frame,topic)})
            x,y=j*176,index*339
            pen.text((x+3,y+4),f"{row['rank']}위 {t:.2f}s",fill=(22,22,22),font=font)
            out_image.paste(frame.resize((176,315)),(x,y+24))
        dark=sum(r["subject_region_median"]<25 for r in frames)
        placeholder=any(x in str(row["caption"]) for x in REVIEW_PLACEHOLDERS)
        warnings=[]
        if placeholder:warnings.append("PLACEHOLDER_CAPTION_MUST_BE_REWRITTEN")
        if dark>=4:warnings.append("DARK_OR_CONTRAST_WEAK_SCENE_RECHECK")
        if row["rank"]==1:warnings.append("RANK_ONE_ACTION_PAYOFF_NOT_VERIFIED")
        findings.append({**row,"sample_count":len(frames),"samples":frames,
                         "dark_or_high_contrast_count":dark,
                         "rank_content_verified":False,
                         "scene_matched_original_caption_verified":False,
                         "source_rights_cleared":False,
                         "review_flags":warnings})
    hook=[]
    for t in (.35,.85,1.45):
        frame=capture_frame(video,t)
        if frame.size!=(360,640):raise ValueError("INVALID_HOOK_FRAME")
        hook.append({"second":t,"subject_region_median":luminance_median(frame,topic)})
    repeats=possible_repeated_subject([{"rank":x["rank"],
                                       "original_title":x["title"]} for x in rows])
    report={
        "schema_version":1,"topic":topic,"rendered_mp4":VIDEO,
        "rendered_mp4_sha256":digest,
        "five_rank_source_provenance_bound":True,
        "actual_video_frames_inspected":35+len(hook),
        "source_ranks":findings,
        "hook_samples":hook,
        "hook_event_verified":False,
        "potential_duplicate_titles":repeats,
        "unready_caption_ranks":[x["rank"] for x in findings
                                 if "PLACEHOLDER_CAPTION_MUST_BE_REWRITTEN" in x["review_flags"]],
        "editorial_score_100":None,"ranking_story_verified":False,
        "third_party_rights_verified":False,
        "youtube_monetization_verified":False,
        "publication_approved":False,
        "status":"DEFAULT_AUTO_EDITORIAL_REVIEW_REQUIRED",
        "next_step":"Examine 35 real ranked frames plus hook; replace poor cuts and author independently justified scene-synchronous captions before considering any 85pt review.",
        "method":"Actual rendered MP4 35 sampled frames; source hash+URL+topic-bound selection and conservative center luminance, no action inference."
    }
    out_image.save(root/"TOP5_STANDARD_35_FRAME_QA.jpg",quality=88,optimize=True)
    (root/"TOP5_STANDARD_EDITORIAL_QA.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Actual standard-auto video editorial review","",
           "Status: **REVIEW ONLY**. 85pt editorial quality, true scene actions and rights remain unverified.","",
           "| Rank | Source title | Dark/7 | Caption | Flags |",
           "|---:|---|---:|---|---|"]
    for x in findings:
        lines.append(f"| {x['rank']} | {x['title'].replace('|','/')} | {x['dark_or_high_contrast_count']} | {str(x['caption']).replace('|','/')} | {', '.join(x['review_flags']) or 'STORY_NOT_CERTIFIED'} |")
    lines.extend(["","The first 2-second hook is visually sampled but the claimed event is unverified.",
                  "Do not auto-replace footage based on X-CLIP relative probabilities alone.",
                  "Do not publish without independent authorship/third-party rights and reused-content review."])
    (root/"TOP5_STANDARD_EDITORIAL_QUEUE.md").write_text(
        "\n".join(lines)+"\n",encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    report=evaluate_standard(args.output)
    print(json.dumps({"topic":report["topic"],
                      "frame_sample_count":report["actual_video_frames_inspected"],
                      "unready_caption_ranks":report["unready_caption_ranks"],
                      "publication_approved":False},ensure_ascii=False))


if __name__=="__main__":
    main()
