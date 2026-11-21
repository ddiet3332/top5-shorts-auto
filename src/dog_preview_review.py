"""Bounded, hash-and-window-checked editorial triage of *actual* cached previews.

Never interpret a preview rejection as license clearance, original-source
ownership, a 100-point whole-video score, or permission to auto-publish.
A new source byte hash or an unreviewed source window reopens manual review.
"""
import json
import math
import re
from pathlib import Path


def _positive_finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def load_preview_rejections(path):
    if path is None or not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1 or
        data.get("review_kind") != "source_hash_and_window_matched_preview_rejections" or
        data.get("publication_approved") is not False):
        raise ValueError("INVALID_PREVIEW_REVIEW_MANIFEST")
    rows = data.get("rejections")
    if not isinstance(rows, list):
        raise ValueError("INVALID_PREVIEW_REVIEW_ROWS")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("INVALID_PREVIEW_REVIEW_ROW")
        rid = row.get("id")
        digest = row.get("source_sha256")
        windows = row.get("reviewed_window_starts_sec")
        samples = row.get("sampled_frame_offsets_sec")
        note = row.get("review_notes")
        if (not isinstance(rid, str) or not re.fullmatch(r"PX-[0-9]+", rid) or
            rid in result or row.get("provider") != "pexels" or
            not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or
            row.get("decision") != "DO_NOT_REPLACE" or
            row.get("rights_status") != "UNVERIFIED" or
            row.get("publication_approved") is not False or
            not isinstance(windows, list) or not windows or
            any(not _positive_finite_number(t) for t in windows) or
            len(set(windows)) != len(windows) or
            not isinstance(samples, list) or len(samples) < 4 or
            any(not _positive_finite_number(t) or t >= 5 for t in samples) or
            not isinstance(note, str) or len(note.strip()) < 70):
            raise ValueError("INVALID_PREVIEW_REVIEW_EVIDENCE")
        result[rid] = row
    return result


def is_evidenced_rejection(item, reviews):
    """Reject only the identical *original asset* and *all* observed preview windows."""
    if not isinstance(item, dict) or item.get("provider") != "pexels":
        return False
    if item.get("status") != "PREVIEW_READY_REVIEW_REQUIRED":
        return False
    row = reviews.get(item.get("id"))
    if row is None or row["source_sha256"] != item.get("sha256"):
        return False
    primary = item.get("preview_start_sec")
    if not _positive_finite_number(primary):
        return False
    actual = [float(primary)]
    alts = item.get("alternative_windows", [])
    if not isinstance(alts, list):
        return False
    for alt in alts:
        if (not isinstance(alt, dict) or
            alt.get("status") != "PREVIEW_READY_REVIEW_REQUIRED" or
            not _positive_finite_number(alt.get("preview_start_sec"))):
            return False
        actual.append(float(alt["preview_start_sec"]))
    reviewed = [float(t) for t in row["reviewed_window_starts_sec"]]
    return len(actual) == len(reviewed) and all(
        abs(a - b) <= 0.01 for a, b in zip(sorted(actual), sorted(reviewed))
    )
