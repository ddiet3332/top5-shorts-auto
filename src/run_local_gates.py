"""Local-only video analysis runner; model weights are explicit inputs.

No network model download, paid API, or automatic semantic certification.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .free_gate_runner import evaluate_manifest
from .local_motion_metrics import extract_motion_metrics
from .local_dog_detector import detect_dog_metrics

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dog-weights", required=True)
    parser.add_argument("--semantic-responses")
    args = parser.parse_args(argv)
    candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("CANDIDATE_MANIFEST_INVALID")
    responses = {}
    if args.semantic_responses:
        responses = json.loads(Path(args.semantic_responses).read_text(encoding="utf-8"))
        if not isinstance(responses, dict):
            raise ValueError("SEMANTIC_RESPONSES_INVALID")
    def detector(path):
        return detect_dog_metrics(path, args.dog_weights)
    report = evaluate_manifest(candidates, args.output, motion_reader=extract_motion_metrics,
                               dog_reader=detector, semantic_responses=responses)
    print(json.dumps({"status": report["status"], "qualified_count": report["qualified_count"],
                      "publication_approved": False}, ensure_ascii=False))
    return 0 if report["qualified_count"] >= 6 else 2

if __name__ == "__main__":
    raise SystemExit(main())
