"""Generate an evidence-based replacement readiness report without changing the render."""
import argparse
import json
from pathlib import Path

from dog_replacement_gate import decide_replacements


def report(profile_path: Path, audition_path: Path) -> dict:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    audition = json.loads(audition_path.read_text(encoding="utf-8"))
    fixed = {label: spec for label, spec in profile["shots"].items()
             if label not in ("rank5", "rank2", "outro")}
    used_ids = {spec["source_id"] for spec in fixed.values()}
    used_actions = {spec["action"] for spec in fixed.values()}
    candidates = {"rank5": [], "rank2": []}
    rejected = []
    for row in audition.get("candidates", []):
        # Old auditions are not clearance or editorial scores; don't invent either.
        if row.get("disposition") == "SELECTED":
            continue
        if row.get("rank_target") in candidates:
            candidates[row["rank_target"]].append(row)
        else:
            rejected.append({"id": row.get("id"), "reason": "NO_TARGET_RANK_OR_UNREVIEWED"})
    decisions = decide_replacements(candidates, incumbent_scores={"rank5": None, "rank2": None},
                                    fixed_source_ids=used_ids, fixed_action_families=used_actions)
    return {
        "schema_version": 1,
        "design_lock": "TOP5_DESIGN_LOCK_V1",
        "candidate_count": sum(map(len, candidates.values())),
        "decisions": [vars(d) for d in decisions],
        "unassigned_auditions": rejected,
        "publication_approved": False,
        "editorial_score": None,
        "next_action": "DISCOVER_AND_REVIEW_CANDIDATES" if not any(
            d.status == "REPLACEMENT_ELIGIBLE" for d in decisions) else "REVIEW_UPGRADE"
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", type=Path, default=Path("sample/dog_editorial_profile_v1.json"))
    p.add_argument("--audition", type=Path, default=Path("sample/dog_replacement_audition.json"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = report(a.profile, a.audition)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DOG_REPLACEMENT_STATUS", result["next_action"], flush=True)


if __name__ == "__main__":
    main()
