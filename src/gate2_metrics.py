"""Deterministic Gate 2 metric evaluator; measurement extraction is separate.

This module never claims detector correctness or human humor certification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

@dataclass(frozen=True)
class Gate2Result:
    passed: bool
    code: str
    metrics: dict[str, float]

def evaluate_gate2(metrics: Mapping[str, Any], thresholds: Mapping[str, float]) -> Gate2Result:
    required = (
        "dog_bbox_area_ratio_median",
        "dog_detection_fraction",
        "static_fraction",
        "late_early_motion_ratio",
    )
    try:
        m = {key: float(metrics[key]) for key in required}
        from math import isfinite
        if not all(isfinite(x) for x in m.values()):
            raise ValueError("nonfinite")
        if not all(0 <= m[k] <= 1 for k in required[:3]) or m[required[3]] < 0:
            raise ValueError("out of range")
        t = {
            "min_dog_bbox_area_ratio": float(thresholds["min_dog_bbox_area_ratio"]),
            "min_dog_detection_fraction": float(thresholds["min_dog_detection_fraction"]),
            "max_static_fraction": float(thresholds["max_static_fraction"]),
            "min_late_early_motion_ratio": float(thresholds["min_late_early_motion_ratio"]),
        }
    except (KeyError, ValueError, TypeError, OverflowError):
        return Gate2Result(False, "REJECT_METRICS_UNAVAILABLE", {})
    if m["dog_bbox_area_ratio_median"] < t["min_dog_bbox_area_ratio"]:
        return Gate2Result(False, "REJECT_SUBJECT_SMALL", m)
    if m["dog_detection_fraction"] < t["min_dog_detection_fraction"]:
        return Gate2Result(False, "REJECT_SUBJECT_ABSENT", m)
    if m["static_fraction"] > t["max_static_fraction"]:
        return Gate2Result(False, "REJECT_STATIC", m)
    if m["late_early_motion_ratio"] < t["min_late_early_motion_ratio"]:
        return Gate2Result(False, "REJECT_NO_TWIST", m)
    return Gate2Result(True, "PASS_NUMERIC_METRICS_ONLY", m)
