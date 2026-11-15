#!/usr/bin/env python3
"""TOP5 100-point editorial scorecard.

A source audition is NOT a completed edited short.
The score remains null until human editorial review of a completed video.
Copyright clearance is a separate mandatory publication gate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

RUBRIC = (
    ("hook_first_2s", "첫 2초 후킹", 20),
    ("humor_payoff", "장면 재미·반전", 25),
    ("ranking_convincing", "TOP5 순위 설득력", 15),
    ("pacing_transitions", "컷 전환·흐름", 15),
    ("creative_captions", "코믹 자막·창작성", 10),
    ("sound_immersion", "사운드·몰입감", 10),
    ("rights_monetization_readiness", "저작권·수익화 준비", 5),
)
TOTAL = sum(maximum for _, _, maximum in RUBRIC)
assert TOTAL == 100

def template(project_id: str, stage: str = "candidate_review") -> dict:
    return {
        "project_id": str(project_id),
        "stage": stage,
        "scoring_protocol": "original_TOP5_100_point",
        "score_status": "NOT_SCORED_COMPLETE_VIDEO_REQUIRED",
        "scores": {key: None for key, _, _ in RUBRIC},
        "total_score": None,
        "production_target": 75,
        "publishing_candidate_target": 85,
        "rights_cleared": False,
        "publication_approved": False,
        "mandatory_gate": "No publication without verified original rights/third-party rights, regardless of score.",
        "rubric": [{"id": key, "name": title, "max_score": maximum}
                   for key, title, maximum in RUBRIC],
    }

def assess(scores: dict, *, edited_video_reviewed: bool,
           rights_cleared: bool = False) -> dict:
    """Accept only explicit human-entered scores for a finished edited video."""
    if not edited_video_reviewed:
        raise ValueError("100점 평가는 완성된 편집 영상의 검수를 필요로 합니다.")
    if set(scores) != {key for key, _, _ in RUBRIC}:
        raise ValueError("7개 기존 평가 항목 모두 필요합니다.")
    for key, _, max_points in RUBRIC:
        value = scores[key]
        if type(value) is not int or not 0 <= value <= max_points:
            raise ValueError(f"{key}: 0~{max_points} 정수 점수가 필요합니다.")
    total = sum(scores.values())
    readiness = ("REWORK" if total < 75 else "IMPROVE" if total < 85 else "PUBLISH_CANDIDATE")
    return {"scores": dict(scores), "total_score": total,
            "content_grade": readiness,
            "rights_cleared": bool(rights_cleared),
            "publication_approved": False,
            "note": "85점 이상도 권리 및 정책 별도 승인 전에는 게시 금지"}

def markdown(card: dict) -> str:
    rows = ["# TOP5 쇼츠 — 기존 100점 만점 평가표", "",
            f"- 프로젝트: {card['project_id']}",
            f"- 단계: {card['stage']}",
            f"- 완성본 총점: **미평가** (후보 영상에 완성본 점수 부여 금지)", "",
            "| 항목 | 최대 점수 | 현재 점수 |",
            "|---|---:|---:|"]
    for item in card["rubric"]:
        rows.append(f"| {item['name']} | {item['max_score']} | 미평가 |")
    rows += ["| **총점** | **100** | **미평가** |",
             "", "- 제작 목표: **75점 이상**",
             "- 게시 후보 목표: **85점 이상**",
             "- 저작권·제3자 권리 검증: **미완료**",
             "- 최종 게시 승인: **아니오**",
             "", "**기준:** GitHub Actions 성공이나 Commons CC 표시만으로 "
             "점수를 채우거나 게시를 승인하지 않습니다.",
             "실제 완성본을 재생하고 확인된 장면만 근거로 점수를 기입합니다.",
             ""]
    return "\n".join(rows)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output")
    p.add_argument("--run", default="unknown")
    p.add_argument("--stage", default="candidate_review")
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(exist_ok=True, parents=True)
    card = template(args.run, args.stage)
    (out / "TOP5_100_POINT_SCORECARD.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "TOP5_100_POINT_SCORECARD.md").write_text(markdown(card), encoding="utf-8")
    print("Original 100-point rubric exported. Final score not fabricated.")

if __name__ == "__main__":
    main()
