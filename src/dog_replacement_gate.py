"""Fail-closed editorial replacement decisions for weak dog TOP5 ranks.

This module does not infer comedy or licensing from motion scores. Candidate
records must carry independent review evidence before an upgrade is eligible.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any

WEAK_RANKS = {"rank5": "PX-9006741", "rank2": "PX-7515923"}
REQUIRED_FIELDS = ("id", "source_url", "creator", "license_url", "sha256",
                   "action_family", "payoff_sec", "start_sec", "duration_sec",
                   "editorial_score", "reviewed_frames", "semantic_review",
                   "rights_status")


@dataclass(frozen=True)
class Decision:
    rank: str
    status: str
    source_id: str
    reason: str


def evaluate_candidate(rank: str, candidate: dict[str, Any],
                       *, used_ids: set[str], used_actions: set[str],
                       incumbent_score: float | None = None) -> Decision:
    """Select only demonstrably better candidates; otherwise retain incumbent."""
    if rank not in WEAK_RANKS:
        raise ValueError("RANK_NOT_ELIGIBLE")
    missing = [field for field in REQUIRED_FIELDS if field not in candidate]
    if missing:
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "MISSING_EVIDENCE:" + ",".join(missing))
    sid = str(candidate["id"])
    if sid in used_ids or candidate["action_family"] in used_actions:
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "DUPLICATE_SOURCE_OR_ACTION")
    if not candidate["source_url"].startswith("https://") or not candidate["license_url"].startswith("https://"):
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "INVALID_SOURCE_PROVENANCE")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(candidate["sha256"])):
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "MISSING_VERIFIED_HASH")
    if candidate["semantic_review"] != "PASS" or candidate["reviewed_frames"] is not True:
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "EDITORIAL_REVIEW_REQUIRED")
    if candidate["rights_status"] != "CLEARED":
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "RIGHTS_REVIEW_REQUIRED")
    try:
        start = float(candidate["start_sec"])
        payoff = float(candidate["payoff_sec"])
        duration = float(candidate["duration_sec"])
        score = float(candidate["editorial_score"])
    except (TypeError, ValueError):
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "INVALID_TIMING_OR_SCORE")
    if not all(math.isfinite(v) for v in (start, payoff, duration, score)):
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "NONFINITE_TIMING_OR_SCORE")
    if not (0 <= start <= payoff < start + 5 <= duration):
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "PAYOFF_OUTSIDE_FIVE_SECONDS")
    if not (0 <= score <= 100) or incumbent_score is None or score <= incumbent_score:
        return Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "NO_PROVEN_EDITORIAL_IMPROVEMENT")
    return Decision(rank, "REPLACEMENT_ELIGIBLE", sid, "VERIFIED_IMPROVEMENT")


def decide_replacements(candidates: dict[str, list[dict[str, Any]]],
                        *, incumbent_scores: dict[str, float | None],
                        fixed_source_ids: set[str],
                        fixed_action_families: set[str]) -> list[Decision]:
    """Deterministic decisions, never reuse a candidate or action family."""
    ids = set(fixed_source_ids)
    actions = set(fixed_action_families)
    decisions = []
    def priority(candidate):
        try:
            score = float(candidate.get("editorial_score") or 0)
            if not math.isfinite(score):
                score = -1
        except (TypeError, ValueError, OverflowError):
            score = -1
        return (-score, str(candidate.get("id", "")))

    for rank in ("rank5", "rank2"):
        pool = sorted(candidates.get(rank, []), key=priority)
        selected = Decision(rank, "NO_UPGRADE", WEAK_RANKS[rank], "EDITORIAL_SOURCE_SHORTAGE")
        for candidate in pool:
            result = evaluate_candidate(rank, candidate, used_ids=ids,
                                        used_actions=actions,
                                        incumbent_score=incumbent_scores.get(rank))
            if result.status == "REPLACEMENT_ELIGIBLE":
                selected = result
                ids.add(result.source_id)
                actions.add(candidate["action_family"])
                break
            # Real candidates exist; report the highest-ranked rejection cause
            # rather than mislabeling them as a source shortage.
            if selected.reason == "EDITORIAL_SOURCE_SHORTAGE":
                selected = result
        decisions.append(selected)
    return decisions
