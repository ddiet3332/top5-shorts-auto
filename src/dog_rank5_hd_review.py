"""Make a genuine 1080x1920 rank-5 dog action audition from the original Pexels asset.

NOT final TOP5, commercial rights clearance, YouTube monetization, or approval.
No source audio is copied, and the original asset is deleted after rendering.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import json
from pathlib import Path
import subprocess

from v12_pexels_audition import download_single_pexels, official_video_id, safe_failure_code

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 24
MAX_SOURCE_BYTES = 125 * 1024 * 1024


def read_manifest(path: Path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1 or data.get("id") != "PX-5263686" or
            data.get("provider") != "pexels" or
            data.get("rank_target") != "rank5" or
            data.get("review_only") is not True or
            data.get("publication_approved") is not False or
            data.get("rights_status") != "UNVERIFIED" or
            data.get("audio_approved") is not False or
            data.get("license_label") != "Pexels License" or
            data.get("license_url") != "https://www.pexels.com/license/" or
            data.get("page_url") !=
                "https://www.pexels.com/video/cute-dog-rolling-on-his-back-5263686/" or
            official_video_id(data) != 5263686 or
            data.get("source_start_sec") != 2.0 or
            data.get("preview_duration_sec") != 5.0):
        raise ValueError("UNTRUSTED_RANK5_REVIEW_SOURCE")
    return data


def render_vertical(source: Path, destination: Path, *, start: float, seconds: float):
    # Portrait crop from ORIGINAL source (not 360x600 review video).
    # Retains natural action speed and minimizes fake enlargements.
    filtergraph=(
        "scale=-2:1920:flags=lanczos,"
        "crop=1080:1920:(iw-ow)/2:0,"
        "drawbox=x=0:y=0:w=iw:h=70:color=black@0.78:t=fill,"
        "drawtext=text='REVIEW ONLY - RANK 5':x=(w-text_w)/2:y=20:"
        "fontsize=30:fontcolor=white,"
        "fps=24,setsar=1,format=yuv420p"
    )
    subprocess.run([
        "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
        "-ss",str(start),"-i",str(source),"-t",str(seconds),
        "-vf",filtergraph,"-an","-c:v","libx264","-preset","fast",
        "-crf","20","-movflags","+faststart",str(destination)
    ],check=True,timeout=150,stdout=subprocess.DEVNULL)


def verify_video(path: Path):
    if not path.is_file() or path.stat().st_size < 15000:
        raise ValueError("REVIEW_MP4_NOT_CREATED")
    result=subprocess.run([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,avg_frame_rate,nb_frames,codec_name:format=duration","-of","json",str(path)
    ],capture_output=True,text=True,timeout=20,check=True)
    data=json.loads(result.stdout)
    video=data["streams"][0]
    duration=float(data["format"]["duration"])
    if (int(video["width"]) != OUTPUT_WIDTH or
            int(video["height"]) != OUTPUT_HEIGHT or
            video["codec_name"] != "h264" or
            not 4.95 <= duration <= 5.05):
        raise ValueError("INVALID_VERTICAL_REVIEW_MP4")
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],
                   check=True,stdout=subprocess.DEVNULL,timeout=90)
    return {"width":OUTPUT_WIDTH,"height":OUTPUT_HEIGHT,"fps":OUTPUT_FPS,
            "duration_sec":round(duration,3),"codec":"h264",
            "full_decode":"PASS","file_bytes":path.stat().st_size}


def create_review(manifest_path, output, *, downloader=None, renderer=None, verifier=None):
    item=read_manifest(Path(manifest_path))
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    source=output/"_PX-5263686_temporary_original.mp4"
    target=output/"PX-5263686_RANK5_ORIGINAL_PORTRAIT_REVIEW_1080x1920.mp4"
    downloader=downloader or download_single_pexels
    renderer=renderer or render_vertical
    verifier=verifier or verify_video
    row={"id":item["id"],"rank":"rank5","provider":"pexels",
         "source_url":item["page_url"],"source_original_sha256":None,
         "original_matches_prior_download":None,
         "review_video_file":None,"render_from_original":False,
         "reviewed_frames":False,"rights_status":"UNVERIFIED",
         "source_audio_copied":False,"publication_approved":False}
    try:
        info=downloader(item,source,max_bytes=MAX_SOURCE_BYTES)
        duration=float(info["duration_sec"])
        if duration<item["source_start_sec"]+item["preview_duration_sec"]+0.2:
            raise ValueError("SOURCE_TOO_SHORT_FOR_REVIEW")
        with source.open("rb") as stream:
            digest=hashlib.file_digest(stream,"sha256").hexdigest()
        row["source_original_sha256"]=digest
        row["original_matches_prior_download"]=(
            digest == item["source_original_sha256_from_run_44879229566"])
        renderer(source,target,start=item["source_start_sec"],
                 seconds=item["preview_duration_sec"])
        row["technical_review"]=verifier(target)
        row["review_video_file"]=target.name
        row["render_from_original"]=True
        row["status"]="HD_REVIEW_READY"
    except (Exception,) as exc:
        row["status"]="HD_REVIEW_FAILED"
        row["failure_code"]=safe_failure_code(exc)
        row["failure_type"]=type(exc).__name__
        target.unlink(missing_ok=True)
    finally:
        source.unlink(missing_ok=True)
    (output/"DOG_RANK5_HD_AUDITION.json").write_text(
        json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DOG_RANK5_HD_AUDITION",row["status"],"rights_status=UNVERIFIED",flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as stream:
            stream.write("ready="+str(row["status"]=="HD_REVIEW_READY").lower()+"\n")
    return row


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,
                   default=Path("sample/dog_rank5_hd_review_v1.json"))
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    create_review(a.manifest,a.output)


if __name__=="__main__":
    main()
