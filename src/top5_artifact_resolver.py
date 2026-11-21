"""Resolve the actual finished TOP5 artifact; never assume all topics are dogs.

Consume GitHub Actions REST artifact JSON from the *triggering run*. This
module only returns a uniquely matching name; it cannot grant publication.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

TOPIC_IDS = {"auto", "dog_surprises", "cat_surprises", "nature_moments",
             "objects_oddities", "human_moments"}


def expected_artifact(workflow: str, run_number: int, artifacts: dict, *, explicit: str = "") -> str:
    if not isinstance(run_number, int) or run_number < 1:
        raise ValueError("INVALID_RUN_NUMBER")
    rows = artifacts.get("artifacts", [])
    if not isinstance(rows, list):
        raise ValueError("INVALID_ARTIFACT_RESPONSE")
    available = [a["name"] for a in rows if isinstance(a, dict)
                 and isinstance(a.get("name"), str)
                 and a.get("expired") is not True]
    if explicit:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,140}", explicit):
            raise ValueError("INVALID_EXPLICIT_ARTIFACT_NAME")
        matches = [x for x in available if x == explicit]
    elif workflow == "TOP5 Topic-Driven Production":
        possible = {f"TOP5-{topic}-review-{run_number}" for topic in TOPIC_IDS}
        matches = [x for x in available if x in possible]
    elif workflow == "TOP5 V32 - Auto stronger original 30s MP4":
        matches = [x for x in available if x == f"TOP5-V32-auto-review-{run_number}"]
    elif workflow == "TOP5 V30 - Auto discovery quality-gated MP4":
        matches = [x for x in available if x == f"TOP5-V30-auto-review-{run_number}"]
    else:
        raise ValueError("UNSUPPORTED_TRIGGER_WORKFLOW")
    if len(matches) != 1:
        raise ValueError("NO_UNIQUE_MATCHING_ARTIFACT")
    return matches[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workflow", required=True)
    p.add_argument("--run-number", type=int, required=True)
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--explicit", default="")
    args = p.parse_args()
    artifacts = json.loads(args.artifacts.read_text(encoding="utf-8"))
    print(expected_artifact(args.workflow, args.run_number,
                            artifacts, explicit=args.explicit))


if __name__ == "__main__":
    main()
