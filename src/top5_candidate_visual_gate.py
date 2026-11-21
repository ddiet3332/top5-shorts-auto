#!/usr/bin/env python3
"""Conservative source-window visibility and named-site checks for universal TOP5.

These inexpensive proxies run BEFORE ranking and MP4 editing. They do NOT
identify actions, validate humor, prove ownership or assign an editorial score.
"""
from __future__ import annotations

import re
import statistics
import subprocess
from pathlib import Path

FRAME_W, FRAME_H = 64, 96
FRAME_BYTES = FRAME_W * FRAME_H
DARK_MEDIAN = 24
STRICT_DARK_FRAMES = 5
MOTION_INTERVAL_SECONDS = 5.8
WEAK_SITE_WORDS = {
    "large", "small", "massive", "natural", "famous", "beautiful",
    "near", "behind", "front", "spectacular", "hidden", "incredible",
    "aerial", "view", "river", "cascading", "water"
}


def named_nature_site(title: str) -> str | None:
    """Only compare explicit named landmarks, not generic 'storm/waterfall'.

    'behind Kawaida Waterfall' and 'side view Kawaida Waterfall' share
    waterfall:kawaida, whereas generic waterfall at unknown location does not.
    This is metadata only; not a claim of identical frames.
    """
    title = re.sub(r"(?i)^file:", "", str(title))
    text = re.sub(r"[_.,()]+", " ", title).casefold()
    matches = re.findall(
        r"\b([a-z][a-z-]{3,})\s+(waterfall|volcano|geyser|canyon|glacier)\b", text
    )
    for place, landmark in matches:
        if place not in WEAK_SITE_WORDS:
            return f"{landmark}:{place}"
    return None


def raw_grayscale_luminance(raw: bytes) -> dict:
    """Analyze centers of six 64x96 grayscale frames, with no ML model."""
    if len(raw) % FRAME_BYTES:
        raise ValueError("INCOMPLETE_VISIBILITY_FRAME")
    count = len(raw) // FRAME_BYTES
    if not 5 <= count <= 8:
        raise ValueError("INSUFFICIENT_VISIBILITY_FRAMES")
    medians = []
    for i in range(count):
        f = raw[i * FRAME_BYTES:(i + 1) * FRAME_BYTES]
        pixels = [f[y * FRAME_W + x] for y in range(12, 84) for x in range(8, 56)]
        medians.append(round(float(statistics.median(pixels)), 2))
    low = sum(x < DARK_MEDIAN for x in medians)
    return {
        "sample_count": count,
        "center_luminance_medians": medians,
        "near_dark_count": low,
        "mostly_dark": low >= STRICT_DARK_FRAMES,
        "method": "original 5.8-second cut, grayscale 64x96, six 1fps center-crop medians",
        "semantic_action_verified": False,
        "editorial_score": None,
    }


def inspect_original_window(path: Path, start: float, *, timeout_sec: int = 32) -> dict:
    if not Path(path).is_file() or start < 0:
        raise ValueError("INVALID_ORIGINAL_WINDOW")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
           "-ss", str(start), "-i", str(path), "-t", str(MOTION_INTERVAL_SECONDS),
           "-an", "-vf", f"fps=1,scale={FRAME_W}:{FRAME_H},format=gray",
           "-f", "rawvideo", "pipe:1"]
    output = subprocess.run(cmd, capture_output=True, check=True,
                            timeout=timeout_sec).stdout
    return raw_grayscale_luminance(output)


def diverse_scene_selection(rows: list[dict], *, required: int = 5) -> tuple[list[dict], list[dict]]:
    """Distinct named nature landmarks before final five-rank selection.

    Unknown location is NOT invented. Reject duplicate named-site candidates
    rather than passing a visually redundant, editorially unverified rank.
    """
    chosen, duplicate_sites = [], []
    used = set()
    for row in rows:
        key = named_nature_site(row["title"])
        if key and key in used:
            duplicate_sites.append({"title": row["title"], "site_key": key,
                                    "reason_code": "REPEATED_NAMED_NATURE_SITE"})
            continue
        chosen.append(row)
        if key:
            used.add(key)
        if len(chosen) >= required:
            break
    return chosen, duplicate_sites
