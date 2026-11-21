#!/usr/bin/env python3
"""Source-bound 15 ORIGINAL-video frames before TOP5 overlays/captions.

The previous V38/V39 model saw finished MP4 crops that contained Korean rank
labels and '장면 내용 검수 필요' graphics. V40 captures three original source
frames per selected rank *inside its actual selected source time window*.
No AI statements, licensing decisions, or automatic caption approvals here.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
from top5_standard_scene_review import source_plan, VIDEO

SIDE=384
RANK_ORDER=(5,4,3,2,1)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def source_times(start,end):
    a,b=float(start),float(end)
    if not 0<=a<b or b-a<2.0:
        raise ValueError("INVALID_ORIGINAL_CUT_WINDOW")
    p=min(.42,(b-a)/10)
    return [round(a+p,3),round((a+b)/2,3),round(b-p,3)]

def frame_at_original(video,sec,*,ffmpeg="ffmpeg"):
    # Preserve the entire source aspect ratio (do not crop away key motion).
    cmd=[ffmpeg,"-nostdin","-hide_banner","-v","error",
         "-ss",str(sec),"-i",str(video),"-frames:v","1",
         "-vf",f"scale={SIDE}:{SIDE}:force_original_aspect_ratio=decrease,"
               f"pad={SIDE}:{SIDE}:(ow-iw)/2:(oh-ih)/2,setsar=1",
         "-f","image2pipe","-vcodec","mjpeg","-q:v","3","pipe:1"]
    raw=subprocess.run(cmd,check=True,capture_output=True,timeout=35).stdout
    result=Image.open(io.BytesIO(raw)).convert("RGB")
    if result.size!=(SIDE,SIDE):
        raise ValueError("INVALID_ORIGINAL_FRAME_SHAPE")
    return result

def plan(root):
    root=Path(root)
    topic,ranks=source_plan(root)
    prov=json.loads((root/"SELECTED_SOURCE_PROVENANCE.json").read_text(encoding="utf-8"))
    sources=prov["selected"]
    if len(sources)!=5 or [s["rank"] for s in sources]!=list(RANK_ORDER):
        raise ValueError("ORIGINAL_PROVENANCE_RANK_ORDER_INVALID")
    repo=Path.cwd().resolve()
    selected=[]
    for src,rank in zip(sources,ranks,strict=True):
        if src["rank"]!=rank["rank"] or src["sha256"]!=rank["source_sha256"]:
            raise ValueError("ORIGINAL_RANK_SOURCE_SHA_MISMATCH")
        raw_path=Path(src["source_path"])
        local=(repo/raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()
        if not local.is_relative_to(repo):
            raise ValueError("SOURCE_OUTSIDE_REPOSITORY_WORKDIR")
        if not local.is_file() or local.stat().st_size!=src["size_bytes"]:
            raise ValueError("SOURCE_ORIGINAL_MISSING_OR_SIZE_CHANGED")
        if digest(local)!=src["sha256"]:
            raise ValueError("SOURCE_ORIGINAL_HASH_CHANGED")
        if (src["rights_verified"] is not False or
            src["publication_approved"] is not False):
            raise ValueError("UNTRUSTED_RIGHTS_STATUS")
        times=source_times(src["source_start_sec"],src["source_end_sec"])
        selected.append({
            "rank":src["rank"],
            "source_path":str(local),
            "original_source_sha256":src["sha256"],
            "source_page":src["source_page"],
            "original_title":rank["title"],
            "original_cut_start":src["source_start_sec"],
            "original_cut_end":src["source_end_sec"],
            "original_times_seconds":times,
            "image_files":[],
            "source_rights_verified":False,
            "actual_action_verified":False,
            "caption_approved":False,
        })
    return topic,selected

def create(root,*,frame_reader=frame_at_original):
    root=Path(root)
    topic,rows=plan(root)
    framesdir=root/"V40_ORIGINAL_SOURCE_FRAMES"
    framesdir.mkdir(parents=True,exist_ok=True)
    width,height=3*SIDE,5*(SIDE+26)
    sheet=Image.new("RGB",(width,height),(246,246,246))
    draw=ImageDraw.Draw(sheet)
    for i,row in enumerate(rows):
        src=Path(row["source_path"])
        for j,t in enumerate(row["original_times_seconds"]):
            im=frame_reader(src,t)
            if im.size!=(SIDE,SIDE):
                raise ValueError("ORIGINAL_FRAME_SIZE_NOT_EXPECTED")
            relative=f"V40_ORIGINAL_SOURCE_FRAMES/rank_{row['rank']}_{j+1}.jpg"
            file=root/relative
            im.save(file,quality=91,subsampling=0)
            row["image_files"].append({
                "relative_file":relative,
                "original_time_seconds":t,
                "image_sha256":digest(file),
                "image_content_has_no_added_top5_template":True,
                "original_video_may_contain_own_titles_or_watermarks":True,
            })
            x,y=j*SIDE,i*(SIDE+26)
            sheet.paste(im,(x,y+26))
            draw.text((x+5,y+5),f"Original rank {row['rank']} at {t:.2f}s",
                      font=ImageFont.load_default(),fill=(20,20,20))
    report={
        "schema_version":1,"topic":topic,
        "method":"3 sampled frames per rank extracted from SHA256-verified original source MP4/WebM cut, never finished TOP5 template",
        "original_video_frame_count":15,
        "rank_count":5,
        "rank_order":list(RANK_ORDER),
        "video_edited_or_published":False,
        "video_under_review":VIDEO,
        "composited_top5_text_added_to_model_images":False,
        "source_may_contain_its_own_original_labels":True,
        "original_action_verified_by_ai":False,
        "korean_caption_approved":False,
        "editorial_score_100":None,
        "source_rights_cleared":False,
        "youtube_monetization_verified":False,
        "publication_approved":False,
        "rows":rows,
    }
    sheet.save(root/"V40_ORIGINAL_15FRAME_STORYBOARD.jpg",quality=88)
    (root/"V40_ORIGINAL_FRAME_MANIFEST.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    report=create(opts.output)
    print(json.dumps({"topic":report["topic"],
                      "original_frames":report["original_video_frame_count"],
                      "publication_approved":False},ensure_ascii=False))

if __name__=="__main__":
    main()
