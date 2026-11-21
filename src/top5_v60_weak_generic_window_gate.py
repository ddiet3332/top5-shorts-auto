"""Exact original SHA/time/topic veto for human-inspected weak generic TOP5 cuts.

Visual evidence from rendered frames does not establish rights, YouTube YPP approval
or action recognition for new footage. Never ban a whole source ID by metadata.
"""
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "review/top5_v60_weak_generic_windows.json"
REASON = "SOURCE_REVIEWED_WEAK_WINDOW"


def reviewed_weak_generic_window(topic, source, start=None, registry_path=REGISTRY):
    """Return the matching human review reason, never a guessed semantic score."""
    if not topic or not isinstance(source, dict):
        return None
    if start is None:
        start = source.get("cut_start_sec")
    if start is None:
        return None
    registry = Path(registry_path)
    if not registry.is_file():
        return None
    evidence = json.loads(registry.read_text(encoding="utf-8"))
    for row in evidence.get("rejected_windows", []):
        if (row["topic"] == topic and
            row["provider"] == source.get("provider") and
            str(row["source_id"]) == str(source.get("id")) and
            row["sha256"] == source.get("sha256") and
            row["source_page"] == source.get("page_url") and
            abs(float(start) - float(row["source_start_sec"])) <= float(row["tolerance_sec"])):
            return row["review_reason"]
    return None
