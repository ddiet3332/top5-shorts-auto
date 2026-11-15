#!/usr/bin/env python3
"""Audition three specifically sourced Wikimedia cat videos for *editorial review only*.

Uses existing Commons API license metadata gate and source downloader. Never
treats source metadata or frame motion as proof of humor, ownership, or YPP.
No originals or audio are published: artifacts are muted 5-sec previews only.
"""
from __future__ import annotations
import json
from pathlib import Path
from top5 import fetch_json, extract_candidates, download_video, probe_duration, motion_highlight
from v12_pexels_audition import make_five_second_preview
from v8_moments import moment_photo

TITLES=[
    "File:Cat chasing a pigeon.webm",
    "File:Moomin1.webm",
    "File:Sammy springt.webm",
]

def main():
    out=Path("output/v28_4_story_candidates")
    clips=out/"previews"
    frames=out/"frames"
    clips.mkdir(parents=True,exist_ok=True)
    frames.mkdir(parents=True,exist_ok=True)
    raw=fetch_json({"action":"query","format":"json","formatversion":"2",
                    "titles":"|".join(TITLES),"prop":"imageinfo",
                    "iiprop":"url|size|mime|extmetadata"})
    found={row["title"]:row for row in extract_candidates(raw)}
    records=[]
    for i,title in enumerate(TITLES,1):
        row={"title":title,"status":"CANDIDATE_ONLY",
             "publication_approved":False,"third_party_rights_verified":False,
             "original_creator_independently_verified":False,
             "youtube_monetization_approved":False,"source_audio_included":False,
             "preview_windows":[]}
        try:
            if title not in found:
                raise ValueError("NOT_IN_LICENSE_FILTERED_METADATA")
            source=found[title]
            row.update({k:source.get(k) for k in ("source_page","author","license",
                       "license_url","source_claim","size_bytes","review_flags")})
            suffix=Path(title).suffix
            tmp=out/f"source_{i:02}{suffix}"
            try:
                download_video(source,tmp)
                duration=probe_duration(tmp)
                row["duration_seconds"]=round(duration,3)
                if duration<3.8:
                    raise ValueError("LESS_THAN_3_8_SECONDS")
                best_start,_=motion_highlight(tmp,duration,seconds=min(5,duration-0.1))
                starts=[0.0]
                if duration>6 and best_start>0.5:
                    starts.append(min(best_start,max(0.,duration-5.01)))
                for j,start in enumerate(starts,1):
                    start=round(float(start),2)
                    preview=clips/f"wiki_{i:02}_moment{j}.mp4"
                    still=frames/f"wiki_{i:02}_moment{j}.jpg"
                    make_five_second_preview(tmp,start,preview)
                    moment_photo(tmp,min(duration-.1,start+2.3),still)
                    row["preview_windows"].append({"start_seconds":start,
                        "preview_file":str(preview.relative_to(out)),
                        "still_file":str(still.relative_to(out)),
                        "surprise_or_fun_verdict":"NOT_YET_HUMAN_REVIEWED"})
                row["status"]="VIDEO_READY_FOR_HUMAN_REVIEW"
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as exc:
            row["status"]="SOURCE_UNAVAILABLE_OR_REJECTED"
            row["failure_type"]=type(exc).__name__
            row["failure_note"]=str(exc)[:120].split("http")[0]
        records.append(row)
        print(title,row["status"],flush=True)
    (out/"V28_4_WIKIMEDIA_AUDITION.json").write_text(
        json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("review-ready",sum(x["status"]=="VIDEO_READY_FOR_HUMAN_REVIEW" for x in records),
          "of",len(records),flush=True)

if __name__=="__main__":
    main()
