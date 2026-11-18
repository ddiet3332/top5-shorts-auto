"""Run free local candidate checks and write auditable fail-closed evidence.

This is not a publication or humor approval engine. Semantic model output
must be supplied by a separate, independently configured local model runner.
"""
from __future__ import annotations
import json
from pathlib import Path
from .quality_gates import predownload_gate, APPROVAL_DEFAULTS
from .source_schema_adapter import normalize_v32_source
from .gate2_metrics import evaluate_gate2
from .gate3_semantic import parse_semantic_response

THRESHOLDS = {
    "min_dog_bbox_area_ratio": 0.08,
    "min_dog_detection_fraction": 0.70,
    "max_static_fraction": 0.30,
    "min_late_early_motion_ratio": 1.30,
}

def evaluate_candidate(candidate, *, motion_reader=None, dog_reader=None, semantic_response=None):
    source = normalize_v32_source(candidate)
    result = {"id": source["id"], "gate_0_passed": False, "gate_1_passed": False,
              "gate_2_passed": False, "gate_3_passed": False, **APPROVAL_DEFAULTS}
    rights = predownload_gate(source)
    result["predownload_code"] = rights.code
    if not rights.accepted:
        result["reject_code"] = rights.code
        return result
    result["gate_0_passed"] = result["gate_1_passed"] = True
    if motion_reader is None or dog_reader is None:
        result["reject_code"] = "REJECT_LOCAL_ANALYSIS_UNAVAILABLE"
        return result
    try:
        motion = motion_reader(source["local_path"])
        dog = dog_reader(source["local_path"])
        metrics = {
            "dog_bbox_area_ratio_median": dog["subject_bbox_fraction"],
            "dog_detection_fraction": dog["subject_detected_fraction"],
            "static_fraction": motion["static_fraction"],
            "late_early_motion_ratio": motion["late_early_motion_ratio"],
        }
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as exc:
        result["reject_code"] = "REJECT_LOCAL_ANALYSIS_UNAVAILABLE"
        result["analysis_error"] = type(exc).__name__
        return result
    decision = evaluate_gate2(metrics, THRESHOLDS)
    result["gate2_code"] = decision.code
    if not decision.passed:
        result["reject_code"] = decision.code
        return result
    result["gate_2_passed"] = True
    if semantic_response is None:
        result["reject_code"] = "REJECT_SEMANTIC_UNAVAILABLE"
        return result
    semantic = parse_semantic_response(semantic_response)
    result["semantic_score"] = semantic.semantic_score
    result["gate3_code"] = semantic.code
    result["gate_3_passed"] = semantic.passed
    result["reject_code"] = None if semantic.passed else semantic.code
    return result

def evaluate_manifest(candidates, output_path, *, motion_reader=None, dog_reader=None,
                      semantic_responses=None):
    rows = []
    for candidate in candidates:
        response = (semantic_responses or {}).get(str(candidate.get("id") or candidate.get("source_page")))
        rows.append(evaluate_candidate(candidate, motion_reader=motion_reader,
                                       dog_reader=dog_reader, semantic_response=response))
    report = {"candidates": rows, "qualified_count": sum(
        all(r[f"gate_{i}_passed"] for i in range(4)) for r in rows),
        "required_distinct_sources": 6, "status": "INSUFFICIENT_QUALIFIED_SOURCES",
        **APPROVAL_DEFAULTS}
    # This report never certifies six distinct source hashes; a separate
    # verified source-selection step is mandatory before status can advance.
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
