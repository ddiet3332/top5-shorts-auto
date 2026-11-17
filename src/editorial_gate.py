"""Fail-closed TOP5 editorial gate. Technical QA is never an editorial score."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

WEIGHTS = {
    "hook": 20,
    "humor_payoff": 25,
    "ranking": 15,
    "flow": 15,
    "creative_captions": 10,
    "sound": 10,
    "rights_monetization": 5,
}
EDITORIAL_THRESHOLD = 80


def assess(scorecard: dict, technical_qa: dict, rights: dict) -> dict:
    dimensions = scorecard.get("dimensions") or {}
    scores = {}
    for name, maximum in WEIGHTS.items():
        value = dimensions.get(name)
        if type(value) not in (int, float) or not 0 <= value <= maximum:
            return {"approved": False, "editorial_score": None,
                    "reason": f"missing_or_invalid_editorial_dimension:{name}",
                    "next_action": "obtain_evidence_based_full_video_audio_review"}
        scores[name] = value
    score = sum(scores.values())
    technical_ok = technical_qa.get("technical_pass") is True
    source_checks = rights.get("sources")
    rights_ok = (rights.get("independent_review_complete") is True
                 and rights.get("youtube_reused_content_review_pass") is True
                 and isinstance(source_checks, list) and len(source_checks) == 5
                 and all(isinstance(s, dict)
                         and s.get("copyright_verified") is True
                         and s.get("likeness_verified") is True
                         and s.get("license_verified") is True
                         for s in source_checks))
    approved = score >= EDITORIAL_THRESHOLD and technical_ok and rights_ok
    return {
        "approved": approved,
        "editorial_score": score,
        "threshold": EDITORIAL_THRESHOLD,
        "technical_pass": technical_ok,
        "rights_verified": rights_ok,
        "youtube_auto_upload": False,
        "reason": ("approved_for_manual_review" if approved else
                   "technical_qa_failed" if not technical_ok else
                   "rights_unverified" if not rights_ok else
                   "editorial_below_80"),
        "next_action": ("manual_upload_only" if approved else
                        "fix_technical_errors" if not technical_ok else
                        "verify_source_rights_and_ypp" if not rights_ok else
                        "replace_weak_clips_and_rebuild"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", required=True, type=Path)
    parser.add_argument("--technical", required=True, type=Path)
    parser.add_argument("--rights", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    result = assess(read(args.scorecard), read(args.technical), read(args.rights))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
