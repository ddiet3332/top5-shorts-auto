"""Fail-closed schema validation for external vision model scores.

No model calls are made here; score acceptance is not humor certification.
"""
from __future__ import annotations
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class SemanticDecision:
    passed: bool
    code: str
    semantic_score: int | None
    components: dict[str, int]

def parse_semantic_response(response: str, min_payoff: int = 3, min_total: int = 9) -> SemanticDecision:
    invalid = SemanticDecision(False, "REJECT_SEMANTIC_PARSE", None, {})
    try:
        payload = json.loads(response)
        if not isinstance(payload, dict) or set(payload) != {"setup", "action", "payoff"}:
            return invalid
        values = {}
        for key in ("setup", "action", "payoff"):
            value = payload[key]
            if type(value) is not int or not 0 <= value <= 5:
                return invalid
            values[key] = value
    except (ValueError, TypeError, KeyError):
        return invalid
    total = sum(values.values())
    if values["payoff"] < min_payoff or total < min_total:
        return SemanticDecision(False, "REJECT_SEMANTIC_WEAK", total, values)
    return SemanticDecision(True, "PASS_SEMANTIC_PRELIMINARY", total, values)
