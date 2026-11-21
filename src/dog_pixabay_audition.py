"""Bounded Pixabay candidate audition using authenticated video lookup.
Never automatically clears third-party rights or promotes a clip to the final video.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request
import urllib.error

from v12_pexels_audition import make_five_second_preview, safe_failure_code

API = "https://pixabay.com/api/videos/"

def download_pixabay(video_id, api_key, destination, *, max_bytes=35*1024*1024, fetch=None, opener=None, media_url=None):
    if not api_key or not isinstance(video_id,int) or isinstance(video_id,bool) or video_id<=0:
        raise ValueError("INVALID_PIXABAY_REQUEST")
    if media_url is None:
        # Legacy fallback for standalone invocation. Production passes a transient
        # media URL captured in the same discovery request, avoiding an extra API call.
        if fetch is None:
            def fetch(url):
                with urllib.request.urlopen(url,timeout=20) as response:
                    return json.load(response)
        payload=fetch(API+"?"+urllib.parse.urlencode({"key":api_key,"id":video_id}))
        hits=payload.get("hits") or []
        hit=next((h for h in hits if h.get("id")==video_id),None)
        if not hit:
            raise ValueError("PIXABAY_ID_NOT_FOUND")
        variants=hit.get("videos") or {}
        variant=next((variants[k] for k in ("medium","small","large","tiny")
                      if isinstance(variants.get(k),dict) and variants[k].get("url")),None)
        if not variant:
            raise ValueError("NO_VIDEO_VARIANT")
        url=variant["url"]
    else:
        url=media_url
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or not (
            parsed.hostname=="pixabay.com" or parsed.hostname.endswith(".pixabay.com")):
        raise ValueError("UNTRUSTED_VIDEO_HOST")
    request=urllib.request.Request(url,headers={"User-Agent":"TOP5-Editorial-Review/1.0"})
    opener=opener or urllib.request.urlopen
    with opener(request,timeout=40) as response:
        final=urllib.parse.urlsplit(response.geturl())
        if final.scheme!="https" or not final.hostname or not (
                final.hostname=="pixabay.com" or final.hostname.endswith(".pixabay.com")):
            raise ValueError("UNTRUSTED_VIDEO_REDIRECT")
        media_type=response.headers.get("Content-Type","").lower()
        if media_type and not (media_type.startswith("video/") or media_type.startswith("application/octet-stream")):
            raise ValueError("NOT_VIDEO_RESPONSE")
        declared=response.headers.get("Content-Length")
        if declared and int(declared)>max_bytes:
            raise ValueError("FILE_TOO_LARGE")
        size=0
        with destination.open("wb") as out:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:
                    break
                size+=len(chunk)
                if size>max_bytes:
                    raise ValueError("FILE_TOO_LARGE")
                out.write(chunk)
    if size<4096:
        raise ValueError("EMPTY_VIDEO")
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=noprint_wrappers=1:nokey=1",str(destination)],
                         capture_output=True,text=True,check=True,timeout=25)
    duration=float(probe.stdout.strip())
    if not 5.25<=duration<=120:
        raise ValueError("UNSUPPORTED_DURATION")
    return {"duration_sec":duration,"size_bytes":size}

def load_provisional_rejections(path):
    """Exclude only weak rank5/rank2 audition subjects, not other future uses."""
    path=Path(path)
    if not path.is_file():
        return set()
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("scope")!="rank5_rank2_replacement_only" or data.get("schema_version")!=1:
        raise ValueError("INVALID_REJECTION_CATALOG")
    return {row["id"] for row in data.get("rejections",[])
            if isinstance(row,dict) and isinstance(row.get("id"),str)
            and row["id"].startswith("PB-") and row["id"][3:].isdigit()}


def recover_cached_previews(output, rejected_ids):
    """Only reuse a local, existing, well-named preview: never assume a cache hit is a new download."""
    evidence = output / "DOG_PIXABAY_AUDITION_RESULTS.json"
    if not evidence.is_file():
        return []
    try:
        data = json.loads(evidence.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or data.get("provider") != "pixabay":
        return []
    ready = []
    seen = set()
    for row in data.get("candidates", []):
        if not isinstance(row, dict):
            continue
        sid = row.get("id")
        if not isinstance(sid, str) or not sid.startswith("PB-") or not sid[3:].isdigit():
            continue
        if sid in seen or sid in rejected_ids or row.get("status") != "PREVIEW_READY_REVIEW_REQUIRED":
            continue
        name = sid + "_preview.mp4"
        media = output / name
        if row.get("preview_file") != name or not media.is_file() or media.stat().st_size == 0:
            continue
        seen.add(sid)
        ready.append({**row, "preview_origin": "CACHED_PREVIOUS_RUN",
                      "rights_status": "UNVERIFIED", "semantic_review": "UNVERIFIED",
                      "reviewed_frames": False, "editorial_score": None,
                      "publication_approved": False})
    return ready[:12]


def resume_cached_pixabay_queue(output, rejection_file=Path("sample/dog_editorial_rejections_v1.json")):
    """Refresh review metadata from local previews without any network request."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rejected = load_provisional_rejections(rejection_file)
    recovered = recover_cached_previews(output, rejected)
    allowed = {row["id"] for row in recovered}
    for preview in output.glob("PB-*_preview.mp4"):
        if preview.stem.removesuffix("_preview") not in allowed:
            preview.unlink(missing_ok=True)
    result = {
        "status": "PREVIEW_READY" if recovered else "NO_PREVIEW",
        "provider": "pixabay", "candidates": recovered,
        "new_preview_count": 0, "cached_preview_count": len(recovered),
        "skipped_provisionally_rejected_ids": sorted(rejected),
        "publication_approved": False
    }
    (output/"DOG_PIXABAY_AUDITION_RESULTS.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


def audition_pixabay(discovery_path,output,api_key,*,max_items=4,downloader=None,previewer=None,media_index=None,rejection_file=Path("sample/dog_editorial_rejections_v1.json")):
    if not 0<=max_items<=6:
        raise ValueError("MAX_ITEMS_EXCEEDED")
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    payload=json.loads(Path(discovery_path).read_text(encoding="utf-8"))
    rejected=load_provisional_rejections(rejection_file)
    recovered = recover_cached_previews(output, rejected)
    recovered_ids = {row["id"] for row in recovered}
    pool=[r for r in payload.get("candidates",[])
          if r.get("provider")=="pixabay" and r.get("id") not in rejected
          and r.get("id") not in recovered_ids]
    run=os.environ.get("GITHUB_RUN_ID","0")
    offset=int(run)%len(pool) if pool and run.isdigit() else 0
    rotated=pool[offset:]+pool[:offset]
    selected, creators=[],set()
    # First sample across different uploaders; avoid four near-identical pet shots.
    for item in rotated:
        creator=str(item.get("creator","")).casefold().strip()
        if creator and creator not in creators:
            selected.append(item)
            creators.add(creator)
        if len(selected)>=max_items:
            break
    if len(selected)<max_items:
        selected.extend(item for item in rotated if item not in selected)
        selected=selected[:max_items]
    downloader=downloader or download_pixabay
    previewer=previewer or make_five_second_preview
    rows=[]
    for item in selected:
        sid=item.get("id","")
        if not isinstance(sid,str) or not sid.startswith("PB-") or not sid[3:].isdigit():
            continue
        raw=output/(sid+".mp4")
        preview=output/(sid+"_preview.mp4")
        row={"id":sid,"source_url":item.get("source_url"),"creator":item.get("creator",""),
             "license_url":"https://pixabay.com/service/license-summary/",
             "preview_origin":"NEW_THIS_RUN",
             "rights_status":"UNVERIFIED","semantic_review":"UNVERIFIED",
             "reviewed_frames":False,"editorial_score":None,"publication_approved":False}
        try:
            if not api_key:
                raise ValueError("NO_API_KEY")
            if media_index is None:
                info=downloader(int(sid[3:]),api_key,raw)
            else:
                url=media_index.get(sid)
                if not isinstance(url,str):
                    raise ValueError("MEDIA_INDEX_MISSING_FOR_CANDIDATE")
                info=downloader(int(sid[3:]),api_key,raw,media_url=url)
            with raw.open("rb") as f:
                row["sha256"]=hashlib.file_digest(f,"sha256").hexdigest()
            row["duration_sec"]=info["duration_sec"]
            previewer(raw,0,preview)
            row["preview_file"]=preview.name
            row["status"]="PREVIEW_READY_REVIEW_REQUIRED"
        except (ValueError,OSError,RuntimeError,subprocess.SubprocessError,TimeoutError) as exc:
            row["status"]="AUDITION_FAILED"
            row["failure_code"]=safe_failure_code(exc)
            if isinstance(exc,urllib.error.HTTPError):
                row["http_status"]=exc.code
            preview.unlink(missing_ok=True)
        finally:
            raw.unlink(missing_ok=True)
        rows.append(row)
    # Keep at most 12 actionable previews across 24-hour API search cycles.
    # Old previews retain their file on disk; no new API request or download is implied.
    pending = [row for row in rows if row["status"]=="PREVIEW_READY_REVIEW_REQUIRED"]
    pending += recovered
    pending = pending[:12]
    valid = {row["id"] for row in pending}
    for preview in output.glob("PB-*_preview.mp4"):
        if preview.stem.removesuffix("_preview") not in valid:
            preview.unlink(missing_ok=True)
    failures = [row for row in rows if row["status"]!="PREVIEW_READY_REVIEW_REQUIRED"]
    candidates = pending + failures
    result={"status":"PREVIEW_READY" if pending else "NO_PREVIEW",
            "provider":"pixabay","candidates":candidates,
            "new_preview_count":sum(row.get("preview_origin")=="NEW_THIS_RUN" for row in pending),
            "cached_preview_count":sum(row.get("preview_origin")=="CACHED_PREVIOUS_RUN" for row in pending),
            "skipped_provisionally_rejected_ids":sorted(rejected),
            "publication_approved":False}
    (output/"DOG_PIXABAY_AUDITION_RESULTS.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--discovery",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--media-index",type=Path)
    parser.add_argument("--rejection-file",type=Path,default=Path("sample/dog_editorial_rejections_v1.json"))
    parser.add_argument("--reuse-cached-only",action="store_true")
    args=parser.parse_args()
    if args.reuse_cached_only:
        result=resume_cached_pixabay_queue(args.output,args.rejection_file)
    else:
        media_index=json.loads(args.media_index.read_text(encoding="utf-8")) if args.media_index else None
        result=audition_pixabay(args.discovery,args.output,os.environ.get("PIXABAY_API_KEY",""),
                               media_index=media_index,rejection_file=args.rejection_file)
    print("PIXABAY_AUDITION",result["status"],len(result["candidates"]))

if __name__=="__main__":
    main()
