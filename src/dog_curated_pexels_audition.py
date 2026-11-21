#!/usr/bin/env python3
"""Bounded official-Pexels dog footage audition, WITHOUT a Pexels API key.

Candidate pages are manually curated. Official download redirects must pass the
existing trusted-host check. No scraping, login bypass, raw source redistribution,
editorial score fabrication, source audio use, or automatic publication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from v12_pexels_audition import (download_single_pexels, make_five_second_preview,
                                 official_video_id, safe_failure_code)
from v8_moments import window_candidates, moment_photo

MAX_ASSETS = 3
MAX_SINGLE_BYTES = 125 * 1024 * 1024


def load_catalog(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("publication_approved") is not False:
        raise ValueError("INVALID_CURATED_DOG_CATALOG")
    sources = data.get("sources", [])
    if not isinstance(sources, list) or not 1 <= len(sources) <= 16:
        raise ValueError("INVALID_CURATED_SOURCE_COUNT")
    ids, actions = set(), set()
    for item in sources:
        if not isinstance(item, dict) or not re.fullmatch(r"PX-[0-9]+",str(item.get("id", ""))):
            raise ValueError("INVALID_CURATED_ID")
        if item["id"] in ids or official_video_id(item) != int(item["id"][3:]):
            raise ValueError("CURATED_SOURCE_ID_MISMATCH")
        if item.get("license_url") != "https://www.pexels.com/license/":
            raise ValueError("UNEXPECTED_LICENSE_URL")
        if item.get("rank_target") not in ("rank5", "rank2"):
            raise ValueError("INVALID_TARGET_RANK")
        if not item.get("creator") or item.get("reviewed_frames") is not False:
            raise ValueError("INVALID_REVIEW_STATE")
        if item.get("editorial_score") is not None or item.get("publication_approved") is not False:
            raise ValueError("PREAPPROVED_OR_SCORED_CANDIDATE")
        family = item.get("action_family_hypothesis")
        if not isinstance(family,str) or not re.fullmatch(r"[a-z0-9_]{3,40}",family):
            raise ValueError("INVALID_ACTION_FAMILY")
        ids.add(item["id"])
        actions.add(family)
    return sources


def _safe_row(item):
    return {
        "id":item["id"],"provider":"pexels","source_url":item["page_url"],
        "creator":item["creator"],"license_url":item["license_url"],
        "rank_target":item["rank_target"],
        "action_family_hypothesis":item["action_family_hypothesis"],
        "status":"NOT_DOWNLOADED","preview_origin":None,
        "reviewed_frames":False,"semantic_review":"UNVERIFIED",
        "rights_status":"UNVERIFIED","editorial_score":None,
        "source_audio_approved":False,"publication_approved":False
    }


def audition(catalog, output, *, max_assets=MAX_ASSETS, downloader=None, previewer=None,
            window_picker=None, image_maker=None):
    if not 1 <= max_assets <= MAX_ASSETS:
        raise ValueError("AUDITION_BUDGET_EXCEEDED")
    sources = load_catalog(Path(catalog))
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    downloader = downloader or download_single_pexels
    previewer = previewer or make_five_second_preview
    window_picker = window_picker or window_candidates
    image_maker = image_maker or moment_photo
    records = []
    for item in sources[:max_assets]:
        row = _safe_row(item)
        sid = item["id"]
        raw = output / (sid+"_temporary.mp4")
        clip = output / (sid+"_preview.mp4")
        stills = [output / (sid+f"_frame{i}.jpg") for i in range(3)]
        try:
            info = downloader(item,raw,max_bytes=MAX_SINGLE_BYTES)
            duration = float(info["duration_sec"])
            if not 5.25 <= duration <= 90:
                raise ValueError("INVALID_SHORT_DURATION")
            with raw.open("rb") as fd:
                sha = hashlib.file_digest(fd,"sha256").hexdigest()
            windows = window_picker(raw,duration,seconds=5.0,count=2,max_scan=45)
            window = windows[0]
            start = max(0.0,min(float(window["start"]),duration-5.15))
            previewer(raw,start,clip)
            if not clip.is_file() or clip.stat().st_size < 2000:
                raise ValueError("INVALID_PREVIEW")
            positions = (start+0.5,start+2.5,start+4.5)
            for position,frame in zip(positions,stills):
                image_maker(raw,min(duration-0.2,position),frame)
                if not frame.is_file() or not frame.stat().st_size:
                    raise ValueError("INVALID_FRAME")
            row.update({
                "status":"PREVIEW_READY_REVIEW_REQUIRED",
                "preview_origin":"NEW_THIS_RUN",
                "preview_file":clip.name,
                "frame_files":[p.name for p in stills],
                "sha256":sha,"duration_sec":round(duration,3),
                "preview_start_sec":round(start,2),
                "motion_proxy_not_comedy_score":window.get("motion"),
                "confirmed_funny_payoff":False,
            })
        except (OSError,RuntimeError,ValueError,TimeoutError,Exception) as exc:
            # Contain all upstream and FFmpeg failures: rights gate remains closed.
            row["status"]="AUDITION_FAILED"
            row["failure_code"]=safe_failure_code(exc)
            row["failure_type"]=type(exc).__name__
            clip.unlink(missing_ok=True)
            for p in stills:
                p.unlink(missing_ok=True)
        finally:
            raw.unlink(missing_ok=True)
        records.append(row)
        print("CURATED_PEXELS",sid,row["status"],flush=True)
    result={
        "status":"PREVIEW_READY" if any(x["status"]=="PREVIEW_READY_REVIEW_REQUIRED"
                                        for x in records) else "NO_PREVIEW",
        "provider":"pexels","method":"Official individual Pexels page download, no API key",
        "candidates":records,"new_preview_count":sum(x["status"]=="PREVIEW_READY_REVIEW_REQUIRED"
                                                       for x in records),
        "publication_approved":False,"rights_status":"UNVERIFIED",
        "next_action":"HUMAN_VISUAL_AND_RIGHTS_REVIEW",
    }
    (output/"DOG_CURATED_PEXELS_AUDITION_RESULTS.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def resume(catalog, output):
    sources = load_catalog(Path(catalog))
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    file=output/"DOG_CURATED_PEXELS_AUDITION_RESULTS.json"
    try:
        previous=json.loads(file.read_text(encoding="utf-8"))
    except (OSError,ValueError):
        previous={"candidates":[]}
    seen={row.get("id"):row for row in previous.get("candidates",[])
          if isinstance(row,dict)}
    rows=[]
    for item in sources:
        row=seen.get(item["id"])
        if not row:
            continue
        clip=output/(item["id"]+"_preview.mp4")
        if (row.get("status")=="PREVIEW_READY_REVIEW_REQUIRED"
                and clip.is_file() and clip.stat().st_size >= 2000
                and row.get("preview_file")==clip.name):
            rows.append({**_safe_row(item),**row,"preview_origin":"CACHED_PREVIOUS_RUN",
                         "reviewed_frames":False,"semantic_review":"UNVERIFIED",
                         "rights_status":"UNVERIFIED","editorial_score":None,
                         "publication_approved":False})
    result={
        "status":"PREVIEW_READY" if rows else "NO_PREVIEW",
        "provider":"pexels","candidates":rows,
        "new_preview_count":0,"cached_preview_count":len(rows),
        "publication_approved":False,"rights_status":"UNVERIFIED",
        "next_action":"HUMAN_VISUAL_AND_RIGHTS_REVIEW",
    }
    file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",type=Path,default=Path("sample/dog_curated_pexels_v1.json"))
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--resume-only",action="store_true")
    p.add_argument("--max-assets",type=int,default=MAX_ASSETS)
    args=p.parse_args()
    result=resume(args.catalog,args.output) if args.resume_only else audition(
        args.catalog,args.output,max_assets=args.max_assets)
    print("DOG_CURATED_PEXELS_AUDITION",result["status"],
          len(result["candidates"]),flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as handle:
            handle.write("ready="+str(result["status"]=="PREVIEW_READY").lower()+"\n")


if __name__=="__main__":
    main()
