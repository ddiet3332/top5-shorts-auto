#!/usr/bin/env python3
"""Fail-closed topic recovery for real TOP5 auto renders.

"auto" can move to another already-discovered, metadata-eligible subject ONLY
after a verified source-inventory shortage. Never relabel a failed MP4, reuse a
previous rank, or disguise a renderer/codec/rights error as missing footage.
Explicitly requested topics never silently change.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MP4 = "TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
RECOVERY_REPORT = "TOP5_TOPIC_RECOVERY_QA.json"
INVENTORY_SHORTAGE_TOKENS = (
    "DISTINCT_OBJECT_EVENT_SHORTAGE",
    "SOURCE_SHORTAGE",
    "EDITORIAL_SOURCE_SHORTAGE",
    "NO_DISTINCT_HOOK",
    "insufficient rights-metadata sources",
    "INSUFFICIENT_CANDIDATES",
    "RENDERER_FAILED_OR_SOURCE_SHORTAGE",
)
EXPORT_SUFFIXES = {".mp4", ".json", ".jpg", ".jpeg", ".png", ".md", ".txt", ".csv", ".srt", ".ass"}
MAX_AUTO_ATTEMPTS = 5


def ordered_topics(audit):
    initial = audit.get("topic")
    requested = audit.get("requested_topic")
    if not isinstance(initial, str) or not initial or not isinstance(requested, str):
        raise ValueError("INVALID_DISCOVERY_AUDIT")
    if audit.get("publication_approved") is not False or audit.get("rights_verified") is not False:
        raise ValueError("DISCOVERY_RIGHTS_MUST_REMAIN_UNVERIFIED")
    if requested != "auto":
        if initial != requested:
            raise ValueError("MANUAL_TOPIC_MUST_MATCH_DISCOVERY")
        return [initial]
    standings = audit.get("topic_standings")
    if not isinstance(standings, list):
        raise ValueError("AUTO_STANDINGS_MISSING")
    viable = {}
    for row in standings:
        if not isinstance(row, dict):
            continue
        topic = row.get("topic_id")
        n = row.get("metadata_eligible")
        if (isinstance(topic, str) and topic and
            type(n) is int and n >= 5 and
            topic != initial):
            viable[topic] = row
    if not any(x.get("topic_id") == initial for x in standings):
        raise ValueError("INITIAL_TOPIC_NOT_IN_DISCOVERY")
    # Independent metadata only ranks candidate inventory, NOT creative quality.
    rest = sorted(viable, key=lambda key: (
        -viable[key]["metadata_eligible"],
        -float(viable[key].get("heuristic_score") or 0),
        key,
    ))
    return [initial, *rest][:MAX_AUTO_ATTEMPTS]


def source_shortage(output):
    data = str(output or "")
    return any(token in data for token in INVENTORY_SHORTAGE_TOKENS)


def verified_video(directory, topic, *, probe=None):
    """Verify a fresh attempt's *actual* output, not a prior status message."""
    directory = Path(directory)
    video = directory / MP4
    qa_path = directory / "V32_TECHNICAL_QA.json"
    sources_path = directory / "SELECTED_SOURCE_PROVENANCE.json"
    topic_path = directory / "TOPIC_RECOMMENDATIONS_V32.json"
    if not all(p.is_file() for p in (video, qa_path, sources_path, topic_path)):
        return False, "MISSING_TECHNICAL_OR_SOURCE_ARTIFACTS"
    if video.stat().st_size == 0:
        return False, "EMPTY_MP4"
    try:
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        prov = json.loads(sources_path.read_text(encoding="utf-8"))
        recomm = json.loads(topic_path.read_text(encoding="utf-8"))
        rows = prov.get("selected")
        if (qa.get("topic") != topic or recomm.get("chosen_topic") != topic
            or qa.get("full_decode") != "PASS" or qa.get("source_count") != 5
            or qa.get("video_frames") != 720 or qa.get("exact_720_frames") is not True
            or qa.get("publication_approved") is not False
            or qa.get("source_permissions_fully_cleared") is not False
            or prov.get("publication_approved") is not False
            or prov.get("rights_verified") is not False
            or not isinstance(rows, list) or len(rows) != 5
            or len({r.get("sha256") for r in rows}) != 5
            or not all(
                isinstance(r.get("sha256"), str) and len(r["sha256"]) == 64
                and r.get("rank") == 5-i
                and r.get("rights_verified") is False
                and r.get("publication_approved") is False
                for i, r in enumerate(rows)
            )):
            return False, "RANK_SOURCE_OR_TECHNICAL_EVIDENCE_INVALID"
        if probe is None:
            info = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(video)
            ], text=True, timeout=45))
        else:
            info = probe(video)
        videos = [x for x in info["streams"] if x.get("codec_type") == "video"]
        audios = [x for x in info["streams"] if x.get("codec_type") == "audio"]
        if len(videos) != 1 or len(audios) != 1:
            return False, "ONE_VIDEO_ONE_AUDIO_REQUIRED"
        v, a = videos[0], audios[0]
        if (v.get("codec_name") != "h264" or a.get("codec_name") != "aac"
            or (v.get("width"), v.get("height")) != (1080, 1920)
            or v.get("r_frame_rate") != "24/1"
            or int(v.get("nb_frames", 0)) != 720
            or not math.isclose(float(v.get("duration", 0)), 30., abs_tol=.02)
            or not math.isclose(float(a.get("duration", 0)), 30., abs_tol=.15)
            or not math.isclose(float(info["format"]["duration"]), 30., abs_tol=.15)):
            return False, "VIDEO_OR_AUDIO_STREAM_SHAPE_INVALID"
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            subprocess.SubprocessError, json.JSONDecodeError):
        return False, "INVALID_MEDIA_OR_PROVENANCE_REPORT"
    return True, "TECHNICAL_REVIEW_COPY_VERIFIED"


def candidate_failure_diagnostics(trial):
    """Read per-source failures *before* concluding inventory is exhausted.

    All source windows can be valid even when Wikimedia responds with HTTP 429.
    Do not re-label rate limiting as a missing fifth editorially useful clip.
    """
    report=Path(trial)/"V30_CANDIDATES.json"
    result={"candidate_attempt_count":0,
            "temporary_provider_failures":0,
            "temporary_provider_codes":{},
            "source_rejection_count":0}
    if not report.is_file():
        return result
    try:
        rows=json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(rows,list):
            return result
        result["candidate_attempt_count"]=len(rows)
        for row in rows:
            if not isinstance(row,dict):
                continue
            if row.get("status")=="TEMPORARY_PROVIDER_ERROR":
                result["temporary_provider_failures"]+=1
                code=str(row.get("reason_code","UNKNOWN"))
                result["temporary_provider_codes"][code]=(
                    result["temporary_provider_codes"].get(code,0)+1)
            elif row.get("status")=="REJECTED":
                result["source_rejection_count"]+=1
    except (OSError,ValueError,json.JSONDecodeError):
        result["diagnostic_parse_failed"]=True
    return result


def run_recovery(audit_path, output_root, *, runner=None, probe=None):
    audit_path = Path(audit_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    topics = ordered_topics(audit)
    runner = runner or subprocess.run
    initial = audit["topic"]
    manual = audit["requested_topic"] != "auto"
    attempts = []
    report_path = output_root / RECOVERY_REPORT

    def save(status, *, chosen=None):
        report = {
            "schema_version": 1,
            "requested_topic": audit["requested_topic"],
            "original_discovered_topic": initial,
            "candidate_order": topics,
            "chosen_render_topic": chosen,
            "status": status,
            "attempts": attempts,
            "manual_topic_honored": manual,
            "topic_recovery_is_not_editorial_approval": True,
            "editorial_score_100": None,
            "source_rights_verified": False,
            "youtube_monetization_verified": False,
            "publication_approved": False,
            "youtube_upload_automated": False,
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    if audit.get("status") != "READY_FOR_DOWNLOAD_CHECK":
        save("DISCOVERY_HAS_INSUFFICIENT_METADATA")
        return False
    for index, topic in enumerate(topics):
        trial = output_root / "topic_attempts" / f"{index + 1:02d}_{topic}"
        trial.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(ROOT / "src/top5_auto_v32.py"),
               "--topic", topic, "--output", str(trial)]
        try:
            result = runner(cmd, cwd=ROOT, capture_output=True,
                            text=True, errors="replace", timeout=1100)
        except subprocess.TimeoutExpired:
            attempts.append({"topic": topic, "status": "RENDER_TIMEOUT_FATAL", "exit_code": 124})
            save("RENDER_TIMEOUT_NOT_SOURCE_SHORTAGE")
            return False
        stdout = str(result.stdout or "")
        stderr = str(result.stderr or "")
        (trial / "V46_RENDER_STDOUT_STDERR.txt").write_text(
            (stdout + "\n" + stderr)[-40000:], encoding="utf-8")
        if result.returncode == 0:
            valid, reason = verified_video(trial, topic, probe=probe)
            attempts.append({"topic": topic, "status": reason if valid else "INVALID_SUCCESS_EVIDENCE",
                             "reason": reason, "exit_code": 0})
            if not valid:
                save("RENDER_OR_SOURCE_EVIDENCE_INVALID_FATAL")
                return False
            for candidate in trial.iterdir():
                if candidate.is_file() and candidate.suffix.casefold() in EXPORT_SUFFIXES:
                    shutil.copy2(candidate, output_root / candidate.name)
            # Update the discovery record so subsequent *independent* postrender
            # original-source SHA/frame checks see the real rendered subject.
            final_audit = dict(audit)
            final_audit.update({
                "initial_topic": initial,
                "topic": topic,
                "status": ("RENDERED_AFTER_INVENTORY_RECOVERY"
                           if index else "RENDERED_INITIAL_DISCOVERY_TOPIC"),
                "recovery_attempts": attempts,
                "candidate_count_is_initial_discovery_only": index != 0,
                "rights_verified": False,
                "publication_approved": False,
            })
            audit_path.write_text(json.dumps(final_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            save("TECHNICAL_RENDER_REVIEW_ONLY", chosen=topic)
            print(json.dumps({"rendered_topic": topic, "original_topic": initial,
                              "attempts": len(attempts), "technical_verified": True,
                              "publication_approved": False}, ensure_ascii=False), flush=True)
            return True
        shortage = source_shortage(stdout + "\n" + stderr)
        diagnostic=candidate_failure_diagnostics(trial)
        # A source selector reporting 0/5 after three HTTP 429s did not
        # establish that all candidate videos were unsuitable. Do not
        # immediately hammer the same Wikimedia host with a new topic.
        provider_down=diagnostic["temporary_provider_failures"]>=2
        status=("TRANSIENT_PROVIDER_UNAVAILABLE" if provider_down
                else "REAL_SOURCE_SHORTAGE" if shortage else "NON_SOURCE_RENDER_FAILURE")
        attempts.append({"topic": topic,
                         "status":status,
                         "source_failure_diagnostics":diagnostic,
                         "exit_code": result.returncode,
                         "failure_tail": (stderr or stdout)[-700:]})
        if provider_down:
            save("PROVIDER_FAILURE_NOT_SOURCE_SHORTAGE")
            print(json.dumps({
                "failed_topic":topic,"reason":"PROVIDER_TEMPORARY_UNAVAILABLE",
                "provider_failures":diagnostic["temporary_provider_failures"],
                "next_topic_allowed":False,"publication_approved":False},
                ensure_ascii=False),flush=True)
            return False
        save("TRY_NEXT_VERIFIED_TOPIC" if shortage and not manual and index + 1 < len(topics)
             else "BLOCKED_SOURCE_SHORTAGE" if shortage
             else "NON_SOURCE_RENDER_FAILURE_FATAL")
        print(json.dumps({"failed_topic": topic,
                          "reason": "REAL_SOURCE_SHORTAGE" if shortage else "RENDER_FAILURE",
                          "next_topic_allowed": shortage and not manual and index + 1 < len(topics)},
                         ensure_ascii=False), flush=True)
        if not shortage:
            return False
    save("NO_FIVE_DISTINCT_SOURCE_TOPIC_AVAILABLE")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not run_recovery(args.audit, args.output_root):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
