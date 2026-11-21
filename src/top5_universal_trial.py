#!/usr/bin/env python3
"""Real, independent cross-category V32 source-to-MP4 trial; never publishes.

This does NOT pretend an 85-point score or a rights clearance. It is an
operational test of whether the SAME generic engine can render four families.
A failure remains a failure, with durable diagnostic output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOPIC_FAMILIES = {
    "cat_surprises": ("animals", "동물"),
    "human_moments": ("people", "사람"),
    "objects_oddities": ("objects", "사물"),
    "nature_moments": ("nature", "자연"),
}
OUTPUT_VIDEO = "TOP5_AUTO_V29_REVIEW_1080x1920.mp4"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def catalog_check(topic, catalog):
    if topic not in TOPIC_FAMILIES:
        raise ValueError("UNSUPPORTED_TRIAL_TOPIC")
    families = {row["topic_id"]: row for row in _load(catalog)}
    row = families.get(topic)
    if not row or row.get("category") != TOPIC_FAMILIES[topic][1]:
        raise ValueError("TOPIC_FAMILY_MISMATCH")
    return row


def media_probe(video):
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True, timeout=35,
    )
    return json.loads(completed.stdout)


def assess(topic, output, *, probe=media_probe):
    """Evidence-based status. Technical pass is not an editorial or rights pass."""
    output = Path(output)
    result = {
        "schema_version": 1, "requested_topic": topic,
        "family": TOPIC_FAMILIES[topic][0],
        "status": "BLOCKED_NO_VERIFIED_MP4",
        "technical_pass": False,
        "final_editorial_score_100": None,
        "full_video_editorial_review_verified": False,
        "rights_verified": False, "youtube_monetization_verified": False,
        "publication_approved": False,
        "manual_youtube_upload_only": True,
        "blockers": ["NO_VERIFIED_VIDEO", "EDITORIAL_REVIEW_REQUIRED",
                     "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"],
    }
    video = output / OUTPUT_VIDEO
    technical_path = output / "V32_TECHNICAL_QA.json"
    sources_path = output / "SELECTED_SOURCE_PROVENANCE.json"
    topic_path = output / "TOPIC_RECOMMENDATIONS_V32.json"
    if not all(p.is_file() for p in (video, technical_path, sources_path, topic_path)):
        result["missing"] = [p.name for p in
                             (video, technical_path, sources_path, topic_path) if not p.is_file()]
        return result
    try:
        technical = _load(technical_path)
        sources = _load(sources_path)
        recommendation = _load(topic_path)
        rows = sources.get("selected")
        if (not isinstance(rows, list) or len(rows) != 5 or
            len({r.get("sha256") for r in rows}) != 5 or
            not all(isinstance(r.get("source_page"), str) and
                    r["source_page"].startswith("https://") and
                    isinstance(r.get("sha256"), str) and len(r["sha256"]) == 64 and
                    r.get("rights_verified") is False and
                    r.get("publication_approved") is False for r in rows)):
            raise ValueError("FIVE_DISTINCT_UNCLEARED_SOURCES_REQUIRED")
        if (recommendation.get("chosen_topic") != topic or
            technical.get("topic") != topic or
            technical.get("full_decode") != "PASS" or
            technical.get("source_count") != 5 or
            technical.get("publication_approved") is not False or
            technical.get("source_permissions_fully_cleared") is not False or
            sources.get("publication_approved") is not False or
            sources.get("rights_verified") is not False):
            raise ValueError("TECHNICAL_SOURCE_OR_PUBLISH_GATE_MISMATCH")
        info = probe(video)
        streams = info.get("streams", [])
        v = [s for s in streams if s.get("codec_type") == "video"]
        a = [s for s in streams if s.get("codec_type") == "audio"]
        duration = float(info["format"]["duration"])
        if (len(v) != 1 or len(a) != 1 or
            v[0].get("codec_name") != "h264" or a[0].get("codec_name") != "aac" or
            (v[0].get("width"), v[0].get("height")) != (1080, 1920) or
            v[0].get("r_frame_rate") != "24/1" or
            int(v[0].get("nb_frames", -1)) != 720 or
            not math.isfinite(duration) or not 29.9 < duration < 30.2):
            raise ValueError("MP4_STREAM_SHAPE_INVALID")
        result.update(
            status="TECHNICAL_PASS_REVIEW_ONLY",
            technical_pass=True,
            video_file=video.name,
            video_sha256=_sha256(video),
            source_count=5,
            full_decode_reported="PASS",
            blockers=["WHOLE_VIDEO_EDITORIAL_SCORE_NOT_VERIFIED",
                      "CAPTION_ACTION_AND_RANK_SEMANTICS_NOT_VERIFIED",
                      "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"],
        )
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        result["status"] = "BLOCKED_INVALID_OUTPUT_EVIDENCE"
        result["reason_code"] = type(exc).__name__
        result["blockers"] = ["INVALID_TECHNICAL_OR_SOURCE_EVIDENCE",
                              "EDITORIAL_REVIEW_REQUIRED",
                              "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"]
    return result


def run_trial(topic, output, *, timeout_seconds=1500):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    catalog_check(topic, ROOT / "sample/top5_auto_topics_v30.json")
    command = [sys.executable, str(ROOT / "src/top5_auto_v32.py"),
               "--topic", topic, "--output", str(output.resolve())]
    log_path = output / "TRIAL_EXECUTION_LOG.txt"
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True,
                                   text=True, errors="replace",
                                   timeout=timeout_seconds)
        log_path.write_text((completed.stdout + "\n" + completed.stderr)[-30000:],
                            encoding="utf-8")
        code = completed.returncode
    except subprocess.TimeoutExpired:
        log_path.write_text("TRIAL_TIMEOUT\n", encoding="utf-8")
        code = 124
    result = assess(topic, output)
    result["renderer_exit_code"] = code
    if code != 0:
        result["status"] = "BLOCKED_SOURCE_OR_RENDER"
        result["technical_pass"] = False
        result["blockers"] = ["RENDERER_FAILED_OR_SOURCE_SHORTAGE",
                              "EDITORIAL_REVIEW_REQUIRED",
                              "SOURCE_RIGHTS_AND_YPP_UNVERIFIED"]
    (output / "UNIVERSAL_TOPIC_TRIAL.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", choices=sorted(TOPIC_FAMILIES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_trial(args.topic, args.output)
    print(json.dumps({"topic": args.topic, "status": result["status"],
                      "technical_pass": result["technical_pass"],
                      "publication_approved": False}, ensure_ascii=False))
    if not result["technical_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
