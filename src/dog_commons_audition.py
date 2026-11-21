"""Review-only Commons fallback: bounded downloads, real video probe and 5s previews."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
from urllib.parse import urlsplit

from dog_commons_discovery import trusted
from top5 import motion_highlight, probe_duration, user_agent
from v12_pexels_audition import make_five_second_preview, safe_failure_code

MAX_DOWNLOAD_BYTES = 35 * 1024 * 1024


def download_commons(row, target, *, max_bytes=MAX_DOWNLOAD_BYTES, opener=None):
    if not trusted({**row, "source_page": row.get("source_url"),
                    "author": row.get("creator")}):
        raise ValueError("UNTRUSTED_COMMONS_METADATA")
    request = urllib.request.Request(row["download_url"], headers={
        "User-Agent": user_agent(),
        "Accept": "video/*,application/octet-stream;q=0.8,application/ogg;q=0.7",
    })
    opener = opener or urllib.request.urlopen
    temp = target.with_name(target.name + ".part")
    try:
        with opener(request, timeout=45) as response:
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != "upload.wikimedia.org":
                raise ValueError("UNTRUSTED_COMMONS_REDIRECT")
            content_type = response.headers.get("Content-Type", "").lower().split(";")[0]
            if content_type and not (content_type.startswith("video/") or content_type in (
                    "application/ogg", "application/octet-stream")):
                raise ValueError("NOT_A_VIDEO_RESPONSE")
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError("SOURCE_OVER_FILE_SIZE_LIMIT")
            size = 0
            with temp.open("wb") as stream:
                while True:
                    part = response.read(1024 * 1024)
                    if not part:
                        break
                    size += len(part)
                    if size > max_bytes:
                        raise ValueError("SOURCE_OVER_FILE_SIZE_LIMIT")
                    stream.write(part)
        if size < 50000:
            raise ValueError("EMPTY_OR_INVALID_FILE")
        temp.replace(target)
        return size
    finally:
        temp.unlink(missing_ok=True)


def audition_commons(discovery_path, output, *, max_items=3, downloader=None,
                    probe=None, motion=None, previewer=None, run_id=None):
    if not 0 <= max_items <= 4:
        raise ValueError("AUDITION_LIMIT_EXCEEDED")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(discovery_path).read_text(encoding="utf-8"))
    pool = [row for row in data.get("candidates", [])
            if row.get("provider") == "wikimedia_commons"]
    run = os.environ.get("GITHUB_RUN_ID", "0") if run_id is None else str(run_id)
    offset = int(run) % len(pool) if pool and run.isdigit() else 0
    # Keep clip behaviours diverse within the small batch.
    rotated = pool[offset:] + pool[:offset]
    picks, families = [], set()
    for item in rotated:
        family = item.get("action_family_from_title")
        if family not in families:
            picks.append(item)
            families.add(family)
        if len(picks) >= max_items:
            break
    downloader = downloader or download_commons
    probe = probe or probe_duration
    motion = motion or motion_highlight
    previewer = previewer or make_five_second_preview
    seen_hashes, records = set(), []
    for item in picks:
        sid = item.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"CM-[0-9a-f]{12}", sid):
            continue
        ext = Path(item.get("source_title", "")).suffix.lower()
        if ext not in (".webm", ".ogv", ".ogg", ".mp4"):
            continue
        raw = output / (sid + ext)
        preview = output / (sid + "_preview.mp4")
        row = {"id": sid, "provider": "wikimedia_commons",
               "source_url": item.get("source_url"), "source_title": item.get("source_title"),
               "creator": item.get("creator"), "license": item.get("license"),
               "license_url": item.get("license_url"),
               "action_family_from_title": item.get("action_family_from_title"),
               "semantic_review": "UNVERIFIED", "reviewed_frames": False,
               "rights_status": "UNVERIFIED", "publication_approved": False,
               "editorial_score": None, "source_audio_approved": False}
        try:
            downloader(item, raw)
            with raw.open("rb") as media:
                digest = hashlib.file_digest(media, "sha256").hexdigest()
            if digest in seen_hashes:
                raise ValueError("DUPLICATE_SOURCE")
            seen_hashes.add(digest)
            duration = float(probe(raw))
            if not 5.25 <= duration <= 120:
                raise ValueError("UNSUPPORTED_DURATION")
            start, score = motion(raw, duration, seconds=5)
            if score < 0.45:
                raise ValueError("LOW_MOTION_PROVISIONAL_REJECTION")
            start = min(max(0.0, float(start)), duration - 5.1)
            previewer(raw, start, preview)
            if not preview.is_file() or preview.stat().st_size < 4096:
                raise ValueError("PREVIEW_MISSING_OR_INVALID")
            row.update({"status": "PREVIEW_READY_REVIEW_REQUIRED",
                        "sha256": digest, "duration_sec": round(duration, 3),
                        "motion_score_not_comedy_score": score,
                        "preview_start_sec": round(start, 3), "preview_file": preview.name})
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as exc:
            row.update({"status": "AUDITION_FAILED", "failure_code": safe_failure_code(exc)})
            preview.unlink(missing_ok=True)
        finally:
            raw.unlink(missing_ok=True)
        records.append(row)
    status = "PREVIEW_READY" if any(r["status"] == "PREVIEW_READY_REVIEW_REQUIRED"
                                    for r in records) else "NO_PREVIEW"
    result = {"status": status, "provider": "wikimedia_commons", "candidates": records,
              "publication_approved": False,
              "note": "No automatic rank replacement; footage and licenses need actual review."}
    (output / "DOG_COMMONS_AUDITION_RESULTS.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DOG_COMMONS_AUDITION", status, len(records), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    audition_commons(args.discovery, args.output)


if __name__ == "__main__":
    main()
