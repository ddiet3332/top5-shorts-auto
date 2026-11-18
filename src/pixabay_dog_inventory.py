#!/usr/bin/env python3
"""Pixabay video metadata inventory only. No automatic download or publication."""
import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

API = "https://pixabay.com/api/videos/"

def collect(key, query, opener=urllib.request.urlopen):
    if not key:
        raise ValueError("Pixabay API secret missing")
    params = urllib.parse.urlencode({"key": key, "q": query, "per_page": 30, "safesearch": "true"})
    request = urllib.request.Request(API + "?" + params, headers={"User-Agent": "TOP5ShortsReview/1.0", "Accept": "application/json"})
    with opener(request, timeout=30) as response:
        data = json.load(response)
    items = []
    for hit in data.get("hits", []):
        videos = hit.get("videos") or {}
        variants = [videos.get(name) for name in ("medium", "small", "large", "tiny")]
        variant = next((v for v in variants if isinstance(v, dict) and v.get("url")), {})
        items.append({
            "provider": "pixabay",
            "id": hit.get("id"),
            "page_url": hit.get("pageURL"),
            "tags": hit.get("tags", ""),
            "creator": hit.get("user", ""),
            "duration": hit.get("duration"),
            "preview_width": variant.get("width"),
            "preview_height": variant.get("height"),
            "has_video_variant": bool(variant.get("url")),
            "license_status": "unverified_provider_metadata",
            "rights_verified": False,
            "likeness_verified": False,
            "youtube_reuse_verified": False,
            "approved_for_publication": False
        })
    return {"provider": "pixabay", "query": query, "count": len(items),
            "approved_for_publication": False, "candidates": items}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", default="funny puppy")
    p.add_argument("--output", default="output/PIXABAY_DOG_UNAPPROVED.json")
    args = p.parse_args()
    key = os.environ.get("PIXABAY_API_KEY") or os.environ.get("PIXABAY_API_NAME")
    if not key:
        raise SystemExit("BLOCKED: set PIXABAY_API_KEY (or legacy PIXABAY_API_NAME) GitHub Actions secret")
    try:
        inventory = collect(key, args.query)
    except Exception as e:
        # Do not print API request URLs: query string contains the secret.
        raise SystemExit("BLOCKED: Pixabay API request failed (" + type(e).__name__ + ")")
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Pixabay metadata candidates:", inventory["count"], "; rights approved: 0; publication BLOCKED")

if __name__ == "__main__":
    main()
