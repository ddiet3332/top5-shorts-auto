#!/usr/bin/env python3
"""Rights-conservative Pixabay / public-media fallback for HUMAN TOP5 review.

Uses the *existing* generic source downloader and video renderer; never
claims that human likeness, performance rights, footage ownership, clip
semantics, or YouTube monetization have been cleared.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FALLBACK_VIDEO = "TOP5_REVIEW_1080x1920.mp4"
EXPORT_VIDEO = "TOP5_AUTO_V29_REVIEW_1080x1920.mp4"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def human_plan():
    # None of these titles or labels are based on visual review.
    # Each topic preserves a coherent human skill/movement theme.
    options = [
        {"topic": "놀라운 댄스 동작 TOP5", "category": "people",
         "search_queries": ["dance", "dancing"]},
        {"topic": "놀라운 체조 동작 TOP5", "category": "people",
         "search_queries": ["gymnastics", "gymnast"]},
        {"topic": "사람들의 곡예 장면 TOP5", "category": "people",
         "search_queries": ["acrobat", "acrobatics"]},
    ]
    return {"selected": dict(options[0], selection_method="rights_unverified_stock_fallback"),
            "alternatives": options[1:], "status": "REVIEW_ONLY",
            "editorial_score": None, "rights_verified": False,
            "publication_approved": False}


def media_probe(video):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True, timeout=35)
    return json.loads(result.stdout)


def assess_human_fallback(root, *, probe=media_probe):
    root = Path(root)
    stock = root / "stock_fallback"
    source_dir = stock / "sources"
    render_dir = stock / "render"
    video = render_dir / FALLBACK_VIDEO
    initial = {"schema_version":1, "requested_topic":"human_moments",
               "family":"people", "engine":"generic_verified_stock_review",
               "status":"BLOCKED_STOCK_FALLBACK_NOT_VERIFIED",
               "technical_pass":False, "final_editorial_score_100":None,
               "full_video_editorial_review_verified":False,
               "rights_verified":False, "youtube_monetization_verified":False,
               "publication_approved":False, "manual_youtube_upload_only":True,
               "blockers":["SOURCE_ACQUISITION_OR_RENDER_NOT_VERIFIED",
                           "EDITORIAL_REVIEW_REQUIRED",
                           "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"]}
    manifest=source_dir / "SOURCE_DOWNLOAD_QA.json"
    qa_path=render_dir / "GENERIC_V06_QA.json"
    if not all(p.is_file() for p in (video,manifest,qa_path)):
        return initial
    try:
        sources=load(manifest)
        qa=load(qa_path)
        rows=sources.get("sources")
        if (not isinstance(rows,list) or len(rows)!=5 or
            len({x.get("sha256") for x in rows})!=5 or
            len({(x.get("provider"),str(x.get("id"))) for x in rows})!=5 or
            not all(isinstance(x.get("page_url"),str) and
                    x["page_url"].startswith("https://") and
                    len(x.get("sha256") or "")==64 and
                    x.get("rights_verified") is False and
                    x.get("full_video_decode") is True for x in rows)):
            raise ValueError("FIVE_DISTINCT_DOWNLOADED_HUMAN_SOURCES_REQUIRED")
        # The original downloader may have accepted misleading metadata
        # from a stock provider. Recheck *the selected five* independently.
        from top5_free_source_download import obvious_topic_mismatch
        if any(obvious_topic_mismatch(x.get("tags",""),sources.get("topic",""))
               for x in rows):
            raise ValueError("HUMAN_TOP5_ANIMAL_METADATA_FALSE_POSITIVE")
        if (qa.get("file")!=FALLBACK_VIDEO or
            qa.get("publication_approved") is not False or
            qa.get("rights_verified") is not False or
            qa.get("editorial_score") is not None or
            qa.get("sha256") != sha256(video) or
            not qa.get("technical_checks") or
            not all(val is True for val in qa["technical_checks"].values())):
            raise ValueError("GENERIC_RENDER_OR_PUBLICATION_GATE_MISMATCH")
        info=probe(video)
        video_tracks=[x for x in info.get("streams",[]) if x.get("codec_type")=="video"]
        audio_tracks=[x for x in info.get("streams",[]) if x.get("codec_type")=="audio"]
        if len(video_tracks)!=1 or len(audio_tracks)!=1:
            raise ValueError("VIDEO_OR_AUDIO_STREAM_MISSING")
        v,a=video_tracks[0],audio_tracks[0]
        duration=float(info["format"]["duration"])
        if ((v.get("width"),v.get("height"),v.get("codec_name"))!=(1080,1920,"h264") or
            v.get("r_frame_rate")!="24/1" or
            int(v.get("nb_frames",-1))!=720 or a.get("codec_name")!="aac" or
            not math.isfinite(duration) or not 29.9<duration<30.2):
            raise ValueError("GENERIC_RENDER_STREAM_FORMAT_INVALID")
        exported=root / EXPORT_VIDEO
        shutil.copy2(video,exported)
        initial.update(status="TECHNICAL_PASS_STOCK_FALLBACK_REVIEW_ONLY",
                       technical_pass=True, video_file=exported.name,
                       video_sha256=sha256(exported), source_count=5,
                       selected_human_theme=sources.get("topic"),
                       source_attempts=sources.get("topic_attempts",[]),
                       blockers=["VISUAL_SCENES_AND_RANKS_UNVERIFIED",
                                 "HUMAN_LIKENESS_AND_CREATOR_RIGHTS_UNVERIFIED",
                                 "YOUTUBE_REUSED_CONTENT_AND_MONETIZATION_UNVERIFIED"])
    except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
        initial["reason_code"]=type(exc).__name__
    return initial


def run_human_fallback(root):
    root=Path(root)
    if not os.environ.get("PIXABAY_API_KEY"):
        return {"requested_topic":"human_moments", "family":"people",
                "status":"BLOCKED_PIXABAY_KEY_UNAVAILABLE", "technical_pass":False,
                "final_editorial_score_100":None, "rights_verified":False,
                "publication_approved":False,
                "blockers":["PIXABAY_API_KEY_UNAVAILABLE",
                            "EDITORIAL_REVIEW_REQUIRED",
                            "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"]}
    stock=root/"stock_fallback"
    stock.mkdir(parents=True,exist_ok=True)
    plan=stock/"human_topic_plan.json"
    save(plan,human_plan())
    cmd=[
        [sys.executable,str(ROOT/"src/top5_free_source_download.py"),
         "--plan",str(plan.resolve()),"--output",str((stock/"sources").resolve()),
         "--topic-attempts","3"],
        [sys.executable,str(ROOT/"src/top5_generic_v06_preview.py"),
         "--plan",str(plan.resolve()),"--sources",str((stock/"sources").resolve()),
         "--output",str((stock/"render").resolve())],
    ]
    for index, command in enumerate(cmd,1):
        try:
            completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,
                                     errors="replace",timeout=750 if index==1 else 650)
            (stock/f"stage_{index}_log.txt").write_text(
                (completed.stdout+"\n"+completed.stderr)[-20000:],
                encoding="utf-8")
            if completed.returncode:
                outcome=assess_human_fallback(root)
                outcome["status"]=f"BLOCKED_STOCK_STAGE_{index}"
                outcome["stock_stage_exit_code"]=completed.returncode
                return outcome
        except subprocess.TimeoutExpired:
            (stock/f"stage_{index}_log.txt").write_text("TIMEOUT\n",encoding="utf-8")
            outcome=assess_human_fallback(root)
            outcome["status"]=f"BLOCKED_STOCK_STAGE_{index}_TIMEOUT"
            return outcome
    return assess_human_fallback(root)
