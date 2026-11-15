#!/usr/bin/env python3
"""V25 deterministic technical and editorial-gate QA for review-only 30s TOP5.

Not a subjective comedy score, creator rights audit or monetization approval.
Checks real codec streams/lengths and source uniqueness and enforces no audio
from unverified original footage.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

EXPECTED_SLOTS=["hook","rank5","rank4","rank3","rank2","rank1","outro"]
EXPECTED_SECONDS=[2,4,5,4,6,6,3]


def validate_selection(rows):
    if not isinstance(rows,list) or len(rows)!=5:
        raise ValueError("Five independent real video sources are mandatory")
    keys=[]
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Invalid editorial row")
        provider=row.get("provider")
        if provider not in ("pexels","wikimedia"):
            raise ValueError("Unsupported provider")
        identity=row.get("id") if provider=="pexels" else row.get("title")
        if not identity:
            raise ValueError("Empty source ID")
        keys.append((provider,identity))
        if row.get("audio_approved") is not False:
            raise ValueError("Original source audio not cleared")
        if type(row.get("start_sec")) not in (int,float) or row["start_sec"]<0:
            raise ValueError("Exact positive source start time required")
        if not row.get("display_name"):
            raise ValueError("Rank needs accurate display name")
        if identity in ("File:Jump.webm","File:Katzensprung in Zeitlupe.webm"):
            raise ValueError("Known low-resolution V16/older cut must not return")
    if len(set(keys))!=5:
        raise ValueError("Duplicate source footage cannot fill multiple ranks")
    return keys


def ffprobe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams",
                      "-of","json",str(path)],capture_output=True,text=True,timeout=35,check=True)
    return json.loads(r.stdout)


def inspect_video(path,shotlist,selection):
    keys=validate_selection(selection)
    if not path.is_file():
        raise ValueError("Completed H264/AAC candidate video file absent")
    data=ffprobe(path)
    videos=[x for x in data.get("streams",[]) if x.get("codec_type")=="video"]
    audio=[x for x in data.get("streams",[]) if x.get("codec_type")=="audio"]
    if len(videos)!=1 or len(audio)!=1:
        raise ValueError("Expected one H264 video and one AAC audio stream")
    v=videos[0];a=audio[0]
    if (v.get("codec_name")!="h264" or a.get("codec_name")!="aac"
        or v.get("width")!=1080 or v.get("height")!=1920
        or v.get("r_frame_rate")!="24/1"):
        raise ValueError("Video/AAC codec, 9:16 resolution, or 24fps incorrect")
    vduration=float(v.get("duration",data["format"]["duration"]))
    aduration=float(a.get("duration",data["format"]["duration"]))
    if not 29.85<=vduration<=30.2 or not 29.85<=aduration<=30.2:
        raise ValueError("Actual audio/video streams not 30 seconds")
    if (not isinstance(shotlist,list) or
        [row.get("segment") for row in shotlist]!=EXPECTED_SLOTS or
        [int(row.get("length_seconds",-1)) for row in shotlist]!=EXPECTED_SECONDS):
        raise ValueError("V25 original 30s ranking order/timing changed unexpectedly")
    if any(x.get("original_audio_rights_confirmed") is True for x in shotlist):
        raise ValueError("Source audio must be muted without rights")
    if [x.get("source_title") for x in shotlist[1:6]]!=[
        (f"Pexels {r['id']}" if r["provider"]=="pexels" else r["title"]) for r in selection]:
        raise ValueError("Rendered 5 ranks do not match explicitly selected footage")
    # Real full-frame decode catches errors omitted by ffprobe metadata.
    subprocess.run(["ffmpeg","-hide_banner","-v","error","-i",str(path),
                    "-map","0:v:0","-map","0:a:0","-f","null","-"],
                   capture_output=True,timeout=270,check=True)
    return {
        "status":"TECHNICAL_QA_PASSED_HUMOR_RIGHTS_UNVERIFIED",
        "file":path.name,
        "width":v["width"],"height":v["height"],
        "video_codec":v["codec_name"],"audio_codec":a["codec_name"],
        "frame_rate":v["r_frame_rate"],
        "video_duration_sec":round(vduration,3),
        "audio_duration_sec":round(aduration,3),
        "actual_full_video_audio_decode":"PASS",
        "ranking_source_ids":[r.get("id",r.get("title")) for r in selection],
        "score_out_of_100":None,
        "actual_humor_qa_complete":False,
        "individual_third_party_rights_approved":False,
        "youtube_reused_content_monetization_approved":False,
        "approved_for_publication":False
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output")
    p.add_argument("--selection",default="sample/v22-mixed-selection.json")
    p.add_argument("--video",default="output/TOP5_V25_SITUATION_CAPTIONS_REVIEW_ONLY_1080x1920.mp4")
    args=p.parse_args()
    out=Path(args.output)
    selected=json.loads(Path(args.selection).read_text(encoding="utf-8"))
    shots=json.loads((out/"SHOTLIST_FOR_REVIEW.json").read_text(encoding="utf-8"))
    report=inspect_video(Path(args.video),shots,selected)
    (out/"V25_TECHNICAL_QA.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"V25_TECHNICAL_QA.md").write_text(
        "# V25 TOP5 — real 30-second review-only edit\n\n"+
        "- Full video/audio decode passed (H.264/AAC, 1080x1920/24fps).\n"+
        "- Five distinct original footage sources and accurate ranking slots verified.\n"+
        "- No unapproved source audio; sound effects are synthesized.\n"+
        "- Actual humor/retention, original authorship, third-party rights, "
        "YouTube reused-content monetization **not approved**.\n"+
        "- The original 100-point content grade remains **NOT SCORED** until a "
        "real visual/editorial review of the complete MP4.\n"+
        "- **DO NOT PUBLISH THIS REVIEW MASTER.**\n",encoding="utf-8")
    print("V25 real 30s final full stream decode verified; review-only, no publishing",flush=True)


if __name__=="__main__":
    main()
