"""Bounded Pexels API discovery for dog TOP5 editorial audition.

Discovery is not rights clearance, visual review, or permission to publish.
No API key or download URL is written to evidence.
"""
import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

QUERIES = ("funny dog trick", "dog unexpected reaction", "playful dog")
API = "https://api.pexels.com/videos/search"


def discover(api_key, *, fetch=None, per_page=8, max_results=18):
    if not api_key:
        return {"status": "NO_API_KEY", "candidates": [], "publication_approved": False}
    if not 1 <= per_page <= 12 or not 1 <= max_results <= 36:
        raise ValueError("DISCOVERY_LIMIT_EXCEEDED")
    if fetch is None:
        def fetch(url, key):
            req = urllib.request.Request(url, headers={"Authorization": key, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=18) as response:
                if response.status != 200:
                    raise ValueError("API_RESPONSE_NOT_OK")
                return json.load(response)
    seen = set()
    candidates = []
    errors = []
    for query in QUERIES:
        url = API + "?" + urllib.parse.urlencode({"query": query, "per_page": per_page, "page": 1})
        try:
            payload = fetch(url, api_key)
            for video in payload.get("videos", []):
                vid = video.get("id")
                if not isinstance(vid, int) or vid in seen:
                    continue
                seen.add(vid)
                duration = video.get("duration")
                if not isinstance(duration, (int, float)) or not 5.25 <= duration <= 120:
                    continue
                page = video.get("url", "")
                if not isinstance(page, str) or not page.startswith("https://www.pexels.com/video/"):
                    continue
                user = video.get("user") or {}
                candidates.append({
                    "id": f"PX-{vid}", "source_url": page,
                    "creator": str(user.get("name", ""))[:120],
                    "license_url": "https://www.pexels.com/license/",
                    "duration_sec": duration,
                    "width": video.get("width"), "height": video.get("height"),
                    "discovery_query": query,
                    "editorial_score": None, "semantic_review": "UNVERIFIED",
                    "reviewed_frames": False, "rights_status": "UNVERIFIED",
                    "publication_approved": False,
                    "status": "DISCOVERED_NOT_DOWNLOADED",
                })
                if len(candidates) >= max_results:
                    break
        except (ValueError, OSError, TimeoutError) as exc:
            errors.append({"query": query, "error": type(exc).__name__})
        if len(candidates) >= max_results:
            break
    return {"status": "CANDIDATES_FOUND" if candidates else "SOURCE_SHORTAGE",
            "provider": "pexels", "candidates": candidates,
            "errors": errors, "publication_approved": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = discover(os.environ.get("PEXELS_API_KEY", ""))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DOG_DISCOVERY", result["status"], "count", len(result["candidates"]), flush=True)


if __name__ == "__main__":
    main()
