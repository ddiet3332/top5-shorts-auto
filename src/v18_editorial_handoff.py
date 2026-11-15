#!/usr/bin/env python3
"""V18 human-reviewed source-to-draft handoff.

No AI filename/motion score may approve footage; five distinct, actually
reviewed moments are required. All outputs are REVIEW ONLY, never publication.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

CAPTION_SEGMENTS = ("rank5", "rank4", "rank3", "rank2", "rank1")
ALL_SEGMENTS = ("hook", *CAPTION_SEGMENTS, "outro")


def review_template(index: dict) -> dict:
    """Blank, non-approving decisions for the latest run's actual previews."""
    run_id = index.get("run_id")
    rows = []
    for c in index.get("candidates", []):
        rows.append({
            "title": c["title"],
            "source_page": c.get("source_page", ""),
            "moments": c.get("review_moments", []),
            "editorial_selected_rank": None,
            "reviewed_real_preview": False,
            "visible_behavior": "",
            "why_funny_or_surprising": "",
            "rank_display_name": "",
            "caption_setup": "",
            "caption_payoff": "",
            "chosen_start_sec": None,
            "rights_review_completed": False,
            "publication_approved": False,
        })
    return {
        "source_run_id": run_id,
        "review_status": "AWAITING_VIDEO_QA",
        "hook_caption": "",
        "outro_caption": "",
        "candidates": rows,
        "publication_approved": False,
        "instructions": ("Watch the actual MP4 preview from the referenced Actions run. "
            "Only after five different clips show a clear, distinct payoff may you "
            "mark ranks 5-1. Rights and YouTube monetization remain separate gates."),
    }


def _text(value, label, minimum=4, maximum=180):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{label}: require {minimum}..{maximum} characters of actual observation")
    return value.strip()


def validate_handoff(index: dict, decisions: dict) -> tuple[list, dict, dict]:
    """Validate exact audit membership, inspected 5-second moments, editorial notes."""
    if not isinstance(index, dict) or not isinstance(decisions, dict):
        raise ValueError("Review index and editorial decisions must be objects")
    if index.get("review_status") != "READY_FOR_MANUAL_QA":
        raise ValueError("Source run is not a successful V17 preview audit")
    if type(index.get("run_id")) is not int or index["run_id"] < 1:
        raise ValueError("Invalid source run ID")
    if decisions.get("source_run_id") != index["run_id"]:
        raise ValueError("Editorial decisions do not match the source run")
    if decisions.get("publication_approved") is True:
        raise ValueError("Editorial preview cannot authorize publication")
    candidates = index.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Invalid source manifest")
    by_title = {x["title"]: x for x in candidates if isinstance(x, dict) and x.get("title")}
    if len(by_title) != len(candidates):
        raise ValueError("Ambiguous or duplicate original titles in source manifest")
    choices = decisions.get("candidates", [])
    if not isinstance(choices, list):
        raise ValueError("Candidate decisions must be a list")
    ranks = {}
    used = set()
    for row in choices:
        if not isinstance(row, dict):
            raise ValueError("Invalid review row")
        rank = row.get("editorial_selected_rank")
        if rank is None:
            continue
        if type(rank) is not int or not 1 <= rank <= 5 or rank in ranks:
            raise ValueError("Each selected source must have a unique rank from 1 to 5")
        title = row.get("title")
        if not isinstance(title, str) or title not in by_title or title in used:
            raise ValueError("Selected title missing from audit or duplicated")
        used.add(title)
        if row.get("reviewed_real_preview") is not True:
            raise ValueError(f"Not actually reviewed: {title}")
        if row.get("publication_approved") is True:
            raise ValueError("No editorial row may grant publication permission")
        _text(row.get("visible_behavior"), "visible_behavior", 12)
        _text(row.get("why_funny_or_surprising"), "why_funny_or_surprising", 12)
        _text(row.get("rank_display_name"), "rank_display_name", 2, 25)
        _text(row.get("caption_setup"), "caption_setup", 5, 70)
        _text(row.get("caption_payoff"), "caption_payoff", 5, 70)
        start = row.get("chosen_start_sec")
        if type(start) not in (int, float) or not math.isfinite(start) or start < 0:
            raise ValueError("Chosen start must be a valid number")
        source = by_title[title]
        source_duration = source.get("duration_sec")
        if type(source_duration) not in (int, float) or source_duration < 5.25:
            raise ValueError("Short originals require separate retiming QA before a 5s rank slot")
        if start + 5.20 > source_duration:
            raise ValueError("Insufficient original footage after chosen start")
        preview_windows = source.get("review_moments", [])
        if not any(
            isinstance(m, dict)
            and type(m.get("start_sec")) in (int, float)
            and abs(start - m["start_sec"]) <= 0.03
            and type(m.get("preview_duration_sec")) in (int, float)
            and m["preview_duration_sec"] >= 4.99
            for m in preview_windows
        ):
            raise ValueError("Chosen time must match an actually generated full 5s preview")
        if source.get("publication_approved") is True:
            raise ValueError("Unverified metadata is not a rights approval")
        ranks[rank] = row
    if set(ranks) != set(range(1, 6)):
        raise ValueError("Five unique reviewed ranks are required; do not fill weak clips")
    _text(decisions.get("hook_caption"), "hook_caption", 8, 70)
    _text(decisions.get("outro_caption"), "outro_caption", 8, 70)
    groups = [by_title[ranks[i]["title"]].get("action_group_filename_hint", "other")
              for i in range(5, 0, -1)]
    if len(set(groups)) < 2:
        raise ValueError("Five rankings with the same metadata action group need additional diversity review")
    selections = []
    captions = {"hook": decisions["hook_caption"].strip(),
                "outro": decisions["outro_caption"].strip()}
    phases = {}
    for rank in (5, 4, 3, 2, 1):
        row = ranks[rank]
        text_key = f"rank{rank}"
        captions[text_key] = row["caption_setup"].strip()
        phases[text_key] = [row["caption_setup"].strip(), row["caption_payoff"].strip()]
        selections.append({
            "title": row["title"],
            "provider": "wikimedia",
            "start_sec": round(float(row["chosen_start_sec"]), 2),
            "display_name": row["rank_display_name"].strip(),
            "manual_content_review": True,
            "audio_approved": False,
            "editorial_observation": row["visible_behavior"].strip(),
            "comic_payoff_observation": row["why_funny_or_surprising"].strip(),
        })
    script = {"captions": captions, "phases": phases,
              "review_only": True, "publication_approved": False,
              "source_run_id": index["run_id"]}
    evidence = {
        "source_run_id": index["run_id"],
        "originals": [x["title"] for x in selections],
        "actual_video_editorial_review_reported": True,
        "license_review_complete": False,
        "all_original_audio_muted": True,
        "publication_approved": False,
        "next_step": "Revalidate Commons CC metadata, download selected originals, render review-only draft",
    }
    return selections, script, evidence


def write_handoff(index: dict, decisions: dict, out: Path):
    rows, script, evidence = validate_handoff(index, decisions)
    out.mkdir(parents=True, exist_ok=True)
    (out / "V18_EDITORIAL_SELECTION.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "V18_EDITORIAL_SCRIPT.json").write_text(
        json.dumps(script, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "V18_EDITORIAL_EVIDENCE.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return rows, script, evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", required=True)
    p.add_argument("--decisions", required=True)
    p.add_argument("--output", default="output")
    p.add_argument("--title", default="고양이의 예측 불가 행동 TOP5")
    p.add_argument("--render", action="store_true")
    args = p.parse_args()
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    out = Path(args.output)
    rows, script, _ = write_handoff(index, decisions, out)
    if not args.render:
        print("V18 editorial handoff validated; no media rendered, no publication approval")
        return
    # Existing CC revalidation + 1080x1920/24fps/30s editor; no source audio.
    from top5 import (collect_editorial_selections, write_rights_docs,
                      render_video, DEFAULT_CAPTIONS)
    chosen = collect_editorial_selections(rows, out)
    if len(chosen) != 5:
        raise RuntimeError("Must download five independently reviewed original clips")
    for video in chosen:
        video["audio_approved"] = False
        video["approved_for_publication"] = False
    write_rights_docs(chosen, out)
    captions = dict(DEFAULT_CAPTIONS)
    captions.update(script["captions"])
    names = {x["title"]: x["display_name"] for x in rows}
    rendered = render_video(chosen, out, args.title, captions,
                            narration=None, size="1080x1920",
                            name_overrides=names, caption_phases=script["phases"])
    print(f"V18 REVIEW ONLY: {rendered}; rights NOT approved")


if __name__ == "__main__":
    main()
