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


def nature_event_family(title: str) -> str | None:
    """Recognize broad event classes from filename terms, NEVER the video pixels."""
    text = re.sub(r"(?i)^file:", "", str(title)).casefold()
    for pattern, family in (
        (r"\bgeyser\b", "geyser"),
        (r"\bvolcan(?:o|ic)\b|\beruption\b", "volcano"),
        (r"\bflood(?:ing|s|ed)?\b", "flood"),
        (r"\bwaterfalls?\b|\bcascade\b", "waterfall"),
        (r"\blightning\b|\bthunder(?:storm)?\b", "lightning"),
        (r"\baurora\b|\bnorthern lights\b", "aurora"),
        (r"\btornado\b|\btwister\b", "tornado"),
        (r"\bavalanche\b|\bsnow slide\b", "avalanche"),
        (r"\bglacier\b", "glacier"),
        (r"\bocean\b|\bsurf\b|\bwave\b", "waves"),
        (r"\bhail\b", "hail"),
        (r"\bcloud\b", "cloud"),
    ):
        if re.search(pattern, text):
            return family
    return None


def diverse_scene_selection(rows: list[dict], *, required: int = 5) -> tuple[list[dict], list[dict]]:
    """Diversify five ranked scenes by BOTH named site and broad event type.

    First prefer distinct event families. Only when insufficient, accept a
    *second* scene of the same type at a different named location. Never fill
    three ranks with one event family or two with the same named landmark.
    Metadata keys are hints, not independently verified visual semantics.
    """
    chosen = []
    used_ids = set()
    used_sites = set()
    family_count = {}
    for pass_no in (1, 2):
        for index, row in enumerate(rows):
            if index in used_ids:
                continue
            site = named_nature_site(row["title"])
            family = nature_event_family(row["title"])
            if site and site in used_sites:
                continue
            if family and family_count.get(family, 0) >= pass_no:
                continue
            chosen.append(row)
            used_ids.add(index)
            if site:
                used_sites.add(site)
            if family:
                family_count[family] = family_count.get(family, 0) + 1
            if len(chosen) >= required:
                break
        if len(chosen) >= required:
            break
    excluded = []
    for index, row in enumerate(rows):
        if index in used_ids:
            continue
        site = named_nature_site(row["title"])
        family = nature_event_family(row["title"])
        if site and site in used_sites:
            reason = "REPEATED_NAMED_NATURE_SITE"
        elif family and family_count.get(family, 0) >= 1:
            reason = "REPEATED_NATURE_EVENT_FAMILY"
        else:
            reason = "LOWER_PRIORITY_OR_SAME_EVENT_REVIEW"
        excluded.append({"title": row["title"], "site_key": site,
                         "event_family": family, "reason_code": reason})
    return chosen, excluded


def object_event_family(title: str) -> str | None:
    """Coarse title-only object/mechanism labels, not actual scene understanding."""
    name=re.sub(r"(?i)^file:", "",str(title)).casefold()
    # Real V44 run #44918160276 misread "Domino Roach 2024" as domino
    # physics, although the decoded 35-frame ranked video shows a live roach.
    # Animal keywords veto the object mechanism unless explicitly robotic.
    if (re.search(r"\\b(?:roach|cockroach|beetle|insect)\\b",name)
        and not re.search(r"\\b(?:robot|robotic|animatronic)\\b",name)):
        return None
    for pattern, family in (
        (r"\bdomino(?:es)?\b", "domino"),
        (r"\barduino\b|\belectronic\b|\bcircuit\b", "electronics"),
        (r"\bmarble\b|\bball run\b", "marble_run"),
        (r"\bpendulum\b|\bnewton.?s cradle\b", "pendulum"),
        (r"\bkinetic sculpture\b|\bkinetic art\b", "kinetic_art"),
        (r"\brube goldberg\b|\bmachine\b|\bmechanism\b", "machine"),
        (r"\bspinning top\b|\bgyroscope\b|\bfidget spinner\b", "spinning"),
        (r"\bbouncing ball\b|\bbounce\b", "bouncing"),
        (r"\bbottle flip\b", "bottle_flip"),
        (r"\brobot\b", "robotics"),
        (r"\bmagnet\b", "magnetism"),
        (r"\bgear\b", "gears"),
        (r"\bchain reaction\b", "chain_reaction"),
    ):
        if re.search(pattern,name):
            return family
    return None


def diverse_object_selection(rows: list[dict], *, required: int = 5) -> tuple[list[dict], list[dict]]:
    """At most two source clips per named mechanism family, distinct by type first.

    A TOP5 list of 3 dominos + a ball + a blinking LED has only 3 distinct
    events, not 5 editorially interesting or surprising physical phenomena.
    Unknown titles are NOT considered independent visual evidence; postpone.
    """
    chosen, used_indices = [], set()
    counts = {}
    for pass_no in (1,2):
        for i,row in enumerate(rows):
            if i in used_indices:
                continue
            family=object_event_family(row["title"])
            if family is None or counts.get(family,0)>=pass_no:
                continue
            chosen.append(row)
            used_indices.add(i)
            counts[family]=counts.get(family,0)+1
            if len(chosen)>=required:
                break
        if len(chosen)>=required:
            break
    rejected=[{"title":row["title"],
               "event_family":object_event_family(row["title"]),
               "reason_code":("UNKNOWN_OBJECT_EVENT_TYPE"
                    if object_event_family(row["title"]) is None
                    else "REPEATED_OBJECT_EVENT_FAMILY")}
              for i,row in enumerate(rows) if i not in used_indices]
    return chosen,rejected
