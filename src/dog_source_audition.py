"""Download a tiny bounded sample of discovered Pexels videos for human editorial review.

Never promotes a source to the ranked video or claims rights clearance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from v12_pexels_audition import download_single_pexels, make_five_second_preview, safe_failure_code


def audition(discovery_path: Path, output: Path, *, max_items=2, downloader=None, previewer=None):
    if not 0 <= max_items <= 3:
        raise ValueError("MAX_ITEMS_EXCEEDED")
    discovered = json.loads(discovery_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    downloader = downloader or download_single_pexels
    previewer = previewer or make_five_second_preview
    results = []
    for item in discovered.get("candidates", [])[:max_items]:
        sid = item.get("id", "")
        if not isinstance(sid, str) or not sid.startswith("PX-") or not sid[3:].isdigit():
            continue
        source = {"id": sid, "provider": "pexels", "page_url": item.get("source_url"),
                  "title": sid, "creator": item.get("creator", ""),
                  "license_label": "Pexels License",
                  "license_url": "https://www.pexels.com/license/"}
        raw = output / (sid + ".mp4")
        preview = output / (sid + "_preview.mp4")
        row = {"id": sid, "source_url": source["page_url"],
               "creator": source["creator"], "license_url": source["license_url"],
               "rights_status": "UNVERIFIED", "semantic_review": "UNVERIFIED",
               "reviewed_frames": False, "editorial_score": None,
               "publication_approved": False}
        try:
            info = downloader(source, raw, max_bytes=35 * 1024 * 1024)
            with raw.open("rb") as f:
                row["sha256"] = hashlib.file_digest(f, "sha256").hexdigest()
            row["duration_sec"] = info["duration_sec"]
            previewer(raw, 0, preview)
            row["preview_file"] = preview.name
            row["status"] = "PREVIEW_READY_REVIEW_REQUIRED"
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as exc:
            row["status"] = "AUDITION_FAILED"
            row["failure_code"] = safe_failure_code(exc)
            preview.unlink(missing_ok=True)
        finally:
            raw.unlink(missing_ok=True)
        results.append(row)
    payload = {"status": "PREVIEW_READY" if any(r["status"] == "PREVIEW_READY_REVIEW_REQUIRED" for r in results)
               else "NO_PREVIEW", "candidates": results, "publication_approved": False}
    (output / "DOG_AUDITION_RESULTS.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audition(args.discovery, args.output)
    print("DOG_AUDITION", result["status"], len(result["candidates"]), flush=True)


if __name__ == "__main__":
    main()
