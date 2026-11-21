#!/usr/bin/env python3
"""Inspect the *actual* rendered 30s TOP5 MP4 by rank, not just its metadata.

One independent 35-frame storyboard per episode. Darkness, repetition and
placeholders are conservative RE-REVIEW warnings. No model-inferred action,
creative 85/100 score, license clearance or automatic publishing.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat

VIDEO = "TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
V32_WINDOWS = [(5, 2., 6.), (4, 6., 11.), (3, 11., 15.),
               (2, 15., 21.), (1, 21., 27.)]
REVIEW_PLACEHOLDERS = ("검수 필요", "놓치지 마세요", "장면 다시 보기",
                       "예상 밖 순간", "강아지 순간 포착")
STOP_WORDS = {"file","video","webm","mp4","ogv","from","view","through",
              "side","the","in","at","on","with","for","visible","to"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def plan(topic, root):
    """Bind rank windows to the actual source hashes in its original QA."""
    root = Path(root)
    if topic == "human_moments":
        qa = read(root / "stock_fallback/render/GENERIC_V06_QA.json")
        rows = qa["timeline"]
        captions = qa.get("captions", [])
        if len(rows) != 5 or len(captions) != 5:
            raise ValueError("MISSING_FIVE_HUMAN_RANKS")
        return [{
            "rank": row["rank"],
            "start": float(row["output_start_sec"]),
            "end": float(row["output_end_sec"]),
            "source_sha256": row["source_sha256"],
            "source_url": row["source_url"],
            "caption": captions[i],
            "original_title": str(row.get("source_id", "")),
        } for i,row in enumerate(rows)]
    source = read(root / "SELECTED_SOURCE_PROVENANCE.json")
    reviewed = read(root / "SOURCE_SELECTION_REVIEW.json")
    rows = source["selected"]
    titles = reviewed["items_in_rank_5_to_1_order"]
    if len(rows) != 5 or len(titles) != 5:
        raise ValueError("MISSING_FIVE_V32_RANKS")
    result = []
    for ((rank,start,end), row, named) in zip(V32_WINDOWS,rows,titles):
        if row.get("rank") != rank:
            raise ValueError("RANK_SOURCE_ORDER_MISMATCH")
        result.append({"rank":rank, "start":start, "end":end,
                       "source_sha256":row["sha256"],
                       "source_url":row["source_page"],
                       "caption": named.get("caption") or "장면 내용 검수 필요",
                       "original_title": named["title"]})
    return result


def validate_plan(rows):
    if (len(rows) != 5 or [x["rank"] for x in rows] != [5,4,3,2,1] or
        len({x["source_sha256"] for x in rows}) != 5 or
        not all(len(str(x["source_sha256"])) == 64 for x in rows) or
        not all(x["source_url"].startswith("https://") for x in rows)):
        raise ValueError("RANK_SOURCE_PROVENANCE_INVALID")
    for a,b in zip(rows,rows[1:]):
        if abs(a["end"]-b["start"]) > 0.001:
            raise ValueError("RANK_WINDOWS_NOT_CONTIGUOUS")
    for row in rows:
        if not 0 <= row["start"] < row["end"] <= 30.001:
            raise ValueError("INVALID_RANK_WINDOW")


def sample_times(start,end,n=7):
    if end-start < 2 or n < 3:
        raise ValueError("SHORT_OR_INVALID_WINDOW")
    pad = min(0.3,(end-start)/12)
    return [round(start+pad+(end-start-2*pad)*i/(n-1),3) for i in range(n)]


def capture(video, seconds):
    command = ["ffmpeg","-hide_banner","-v","error","-ss",str(seconds),
               "-i",str(video),"-frames:v","1","-vf","scale=360:640",
               "-f","image2pipe","-vcodec","mjpeg","-q:v","4","pipe:1"]
    return Image.open(io.BytesIO(subprocess.run(
        command,capture_output=True,check=True,timeout=25).stdout)).convert("RGB")


def region(image, topic):
    # Analyze the actual subject area, excluding the title, 5-rank rail and
    # most caption pixels. Both approved visual templates have different crops.
    return (image.crop((80,240,340,410)) if topic == "human_moments"
            else image.crop((85,250,350,432)))


def luminance_median(image, topic):
    gray = region(image,topic).convert("L")
    return int(ImageStat.Stat(gray).median[0])


def possible_repeated_subject(rows):
    """Metadata-based reminder; not a visual duplication finding."""
    collisions = []
    for i,one in enumerate(rows):
        one_tokens = set(re.findall(r"[a-z]{4,}",one["original_title"].lower())) - STOP_WORDS
        for other in rows[i+1:]:
            two_tokens = set(re.findall(r"[a-z]{4,}",other["original_title"].lower())) - STOP_WORDS
            common = one_tokens & two_tokens
            if len(common) >= 2:
                collisions.append({"ranks":[one["rank"],other["rank"]],
                                   "common_title_tokens":sorted(common),
                                   "finding":"TITLE_SIMILARITY_REVIEW_ONLY"})
    return collisions


def evaluate_video(topic,root,*,capture_frame=capture):
    root = Path(root)
    video = root / VIDEO
    trial = read(root / "UNIVERSAL_TOPIC_TRIAL.json")
    if (trial.get("requested_topic") != topic or
        trial.get("technical_pass") is not True or
        trial.get("publication_approved") is not False or
        trial.get("video_sha256") != sha256(video)):
        raise ValueError("ACTUAL_VIDEO_NOT_MATCHING_TECHNICAL_TRIAL")
    rows = plan(topic,root)
    validate_plan(rows)
    font = ImageFont.load_default()
    width,height = 176,315
    sheet=Image.new("RGB",(7*width,5*(height+24)),(243,243,243))
    draw=ImageDraw.Draw(sheet)
    summary=[]
    for row_index,row in enumerate(rows):
        sampled=[]
        for index,t in enumerate(sample_times(row["start"],row["end"])):
            image=capture_frame(video,t)
            if image.size != (360,640):
                raise ValueError("ACTUAL_FRAME_NOT_9_BY_16")
            med=luminance_median(image,topic)
            sampled.append({"video_second":t,"subject_region_median_luma":med})
            xx=index*width
            yy=row_index*(height+24)
            draw.text((xx+2,yy+4),f"#{row['rank']} {t:.2f}s",font=font,fill=(20,20,20))
            sheet.paste(image.resize((width,height)),(xx,yy+24))
        lows=sum(x["subject_region_median_luma"] < 25 for x in sampled)
        caption=str(row["caption"])
        flags=[]
        if any(term in caption for term in REVIEW_PLACEHOLDERS):
            flags.append("PLACEHOLDER_CAPTION_NOT_PUBLISHABLE")
        if lows >= 4:
            flags.append("DARK_OR_HIGH_CONTRAST_CONTENT_REVIEW")
        summary.append({**row, "samples":sampled,
                        "near_dark_sample_count":lows,
                        "possible_weak_visibility":lows>=4,
                        "review_flags":flags,
                        "actual_cut_action_verified":False,
                        "ranking_payoff_verified":False,
                        "source_rights_verified":False})
    duplicate_cues=possible_repeated_subject(rows)
    flags=[(f"RANK_{row['rank']}:{flag}") for row in summary for flag in row["review_flags"]]
    if duplicate_cues:
        flags.append("SIMILAR_SOURCE_TITLES_NEED_DISTINCT_ACTION_REVIEW")
    report={
        "schema_version":1, "topic":topic,
        "video":VIDEO, "video_sha256":trial["video_sha256"],
        "rank_count":5, "samples_per_rank":7,
        "method":"35 actual rendered MP4 frames and conservative region luminance, source QA hash match",
        "editorial_score_100":None, "publication_approved":False,
        "clip_action_verified":False,"whole_video_story_verified":False,
        "rights_verified":False,"youtube_monetization_verified":False,
        "status":"SCENE_EVIDENCE_REVIEW_REQUIRED",
        "ranks":summary, "repeated_title_cues":duplicate_cues,
        "review_flags":flags,
        "warning":"Dark/high-contrast scene is an advisory, not evidence of a missing subject. A semantic human/vision review must examine all sampled frames and the whole footage."
    }
    sheet.save(root / "TOP5_ACTUAL_35FRAME_STORYBOARD.jpg",quality=84,optimize=True)
    (root / "TOP5_SCENE_EVIDENCE.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Actual five-rank, 35-frame editorial review","","No inferred 85/100 score or rights approval. This is a **review-only** visual evidence package.","",
           "| Rank | Source | Dark frames / 7 | Caption | Flags |",
           "|---:|---|---:|---|---|"]
    for row in summary:
        lines.append(f"| {row['rank']} | {row['source_url']} | {row['near_dark_sample_count']} | {str(row['caption']).replace('|','/')} | {', '.join(row['review_flags']) or 'ACTION_REVIEW_REQUIRED'} |")
    lines+=["","## Editor still must verify","",
            "Check the exact 5 selected source actions, the real payoff for each rank, first-second hook, emotional/creative writing, clip continuity, sound and rights for every original. Re-render after correcting weak footage. An automatic technical green result is never a publication pass.","",
            "Scorecard 20 hook + 25 reversal/emotion + 15 ranking + 15 cuts + 10 creative captions + 10 sound + 5 rights = /100. Unscored until actual full video review. Independent copyright/likeness/YPP hard gate always remains."]
    (root / "TOP5_SCENE_REVIEW_CHECKLIST.md").write_text(
        "\n".join(lines)+"\n",encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--topic",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=evaluate_video(args.topic,args.output)
    print(json.dumps({"topic":args.topic,"rank_count":report["rank_count"],
                      "flags":report["review_flags"],
                      "publication_approved":False},ensure_ascii=False))


if __name__=="__main__":
    main()
