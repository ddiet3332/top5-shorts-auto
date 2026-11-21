"""Find licensed Wikimedia Commons dog-video candidates without commercial API keys.

The search result and licence are metadata, not proof of a funny action, authorship,
model releases or YouTube monetization eligibility. Never automatically publish.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from top5 import category_candidates, query_candidates, supported_license

QUERIES = (
    "dog trick", "dog surprise", "dog jumping", "dog rolling",
    "dog chasing", "dog catching", "puppy playing", "dog funny",
    "dog slipping", "dog barking", "dog opens door", "dog shaking water",
    "dog frisbee", "dog trick funny",
)
CATEGORIES = ("Videos of dogs",)
DOG_TERMS = ("dog", "dogs", "puppy", "puppies", "canine", "hound", "hund", "perro", "chien")
ACTIONS = {
    "surprise": ("surpris", "startled", "sudden", "reaction", "unexpected", "scared"),
    "trick": ("trick", "dance", "dancing", "acrobat", "balanc", "skateboard"),
    "fall": ("slip", "fall", "tumble", "fail", "stumble"),
    "roll": ("rolling", "rolls", "rollover", "roll over", "spin"),
    "catch": ("catch", "fetch", "frisbee", "ball"),
    "jump": ("jump", "leap", "hopp", "spring"),
    "chase": ("chase", "chasing", "running", "run"),
    "shake": ("shak", "splash", "water sprinkler"),
    "bark": ("bark", "howl"),
    "door": ("opening door", "opens door", "open door"),
    "play": ("playing", "play", "puppy", "toy"),
}
BLOCKED = ("animation", "cartoon", "film trailer", "music video", "compilation",
           "advert", "gameplay", "ai generated", "movie scene", "television",
           "tetris", "ctwc", "esport", "video game", "dogplayingtetris",
           "compulsive-tail-chasing", "pone.", "scientific paper")


def classify_title(title, *, dog_category=False):
    text = title.casefold()
    if any(b in text for b in BLOCKED):
        return None
    if not dog_category and not any(w in text for w in DOG_TERMS):
        return None
    return next((family for family, terms in ACTIONS.items()
                 if any(term in text for term in terms)), None)


def trusted(row):
    page = urlsplit(str(row.get("source_page", "")))
    media = urlsplit(str(row.get("download_url", "")))
    if page.scheme != "https" or page.hostname != "commons.wikimedia.org":
        return False
    if media.scheme != "https" or media.hostname != "upload.wikimedia.org":
        return False
    if int(row.get("size_bytes") or 0) < 50000 or int(row.get("size_bytes") or 0) > 35 * 1024 * 1024:
        return False
    if not supported_license(row.get("license_url", "")):
        return False
    if not str(row.get("author", "")).strip():
        return False
    return True


def discover_commons(*, search=None, categories=None, max_results=28, per_query=35, excluded_ids=()):
    if not 1 <= max_results <= 36 or not 5 <= per_query <= 50:
        raise ValueError("DISCOVERY_LIMIT_EXCEEDED")
    search = search or query_candidates
    categories = categories or category_candidates
    found, errors = {}, []
    excluded_ids = set(excluded_ids)
    def add(row, route):
        try:
            family = classify_title(str(row.get("title", "")), dog_category=route == "category:Videos of dogs")
            if not family or not trusted(row):
                return
            title = row["title"]
            ident = "CM-" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
            if ident in excluded_ids:
                return
            found.setdefault(title, {
                "id": ident, "provider": "wikimedia_commons",
                "source_title": title, "source_url": row["source_page"],
                "download_url": row["download_url"],
                "creator": row["author"], "size_bytes": row["size_bytes"],
                "license": row.get("license", "CC BY / CC0"),
                "license_url": row["license_url"],
                "action_family_from_title": family, "discovery_route": route,
                "dog_subject_basis": "Wikimedia category metadata" if route == "category:Videos of dogs" else "file title metadata",
                "semantic_review": "UNVERIFIED", "reviewed_frames": False,
                "rights_status": "UNVERIFIED", "publication_approved": False,
                "status": "DISCOVERED_NOT_DOWNLOADED",
            })
        except (ValueError, TypeError, KeyError):
            return

    for query in QUERIES:
        try:
            for row in search(query, per_query=per_query):
                add(row, "search:" + query)
        except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
            errors.append({"route": query, "error": type(exc).__name__})
        if len(found) >= max_results:
            break
    if len(found) < max_results:
        for category in CATEGORIES:
            try:
                for row in categories(category, per_query=per_query):
                    add(row, "category:" + category)
            except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
                errors.append({"route": category, "error": type(exc).__name__})
    # Keep a bounded, varied pool so one common behaviour does not dominate.
    rows = list(found.values())
    rows.sort(key=lambda r: (list(ACTIONS).index(r["action_family_from_title"]), r["id"]))
    selected, overflow, counts = [], [], {}
    for row in rows:
        family = row["action_family_from_title"]
        (selected if counts.get(family, 0) < 4 else overflow).append(row)
        counts[family] = counts.get(family, 0) + 1
    candidates = (selected + overflow)[:max_results]
    status = "CANDIDATES_FOUND" if candidates else (
        "SOURCE_REQUEST_FAILED" if errors else "SOURCE_SHORTAGE")
    return {"status": status, "provider": "wikimedia_commons",
            "candidates": candidates, "errors": errors,
            "method": "CC BY/CC0 provider metadata; dog/action words in file title only",
            "publication_approved": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    catalog=Path("sample/dog_commons_editorial_rejections_v1.json")
    ignored=set()
    if catalog.is_file():
        data=json.loads(catalog.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("review_target") != "rank5_rank2_upgrade_only":
            raise ValueError("INVALID_COMMONS_REJECTION_CATALOG")
        ignored={row["id"] for row in data.get("rejections",[]) if isinstance(row,dict) and isinstance(row.get("id"),str)}
    result = discover_commons(excluded_ids=ignored)
    result["excluded_prior_review_count"]=len(ignored)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DOG_COMMONS_DISCOVERY", result["status"], len(result["candidates"]), flush=True)


if __name__ == "__main__":
    main()
