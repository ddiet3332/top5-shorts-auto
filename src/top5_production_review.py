"""Render and independently check the general-topic mobile review package."""
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from top5_generic_v06_preview import LayoutError, load_reviewed_captions, overlay, run
from top5_publication_gate import CATEGORIES, evaluate
from top5_free_source_download import obvious_topic_mismatch
from top5_remediation import plan as plan_remediation
from top5_review_checks import CUE_TIMES, motion, overlay_checks, soundtrack_checks
from top5_source_contact_sheet import frame
from top5_topic_relevance_gate import topic_metadata_match
from v25_audio_remaster import create_soundtrack

VIDEO = "TOP5_REVIEW_1080x1920.mp4"
REPORT = "GENERIC_V06_QA.json"
LABELS = ("첫 1~3초 후킹", "재미·감동·반전", "TOP5 순위 구성", "장면 연결 및 컷 흐름",
          "창작 자막", "BGM 및 효과음", "권리·수익화 위험 검토")
FFMPEG = ["ffmpeg", "-nostdin", "-hide_banner"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def media_check(args):
    return subprocess.run(FFMPEG + args, check=True, capture_output=True, text=True, timeout=180).stderr


def select_start(path, duration, *, preferred=None, optimize_motion=False, skip=()):
    """Find a six-second cut without sustained black frames."""
    if duration < 6:
        raise ValueError("원본이 6초 미만입니다")
    starts = (preferred, 0, round((duration - 6) / 2, 3), round(duration - 6, 3))
    options = []
    for start in dict.fromkeys(starts):
        if start is None or start in skip or not 0 <= start <= duration - 6 + 0.001:
            continue
        log = media_check(["-xerror", "-ss", str(start), "-i", str(path), "-t", "6",
                           "-vf", "scale=160:-2,blackdetect=d=0.20:pix_th=0.08",
                           "-an", "-f", "null", "-"])
        if "black_start:" not in log:
            if not optimize_motion:
                return start
            metrics = motion(path, start, 6)
            if metrics["sample_count"] >= 22:
                options.append((metrics["peak_change"], metrics["mean_change"], start))
    if options:
        return max(options, key=lambda row: row[:2])[2]
    raise ValueError("원본에서 검은 화면이 없는 6초 구간을 찾지 못했습니다")


def frame_signature(path, timestamp):
    small = frame(path, timestamp).convert("L").resize((9, 8))
    pixels = list(small.getdata())
    signature = 0
    for row in range(8):
        for col in range(8):
            offset = row * 9 + col
            signature = (signature << 1) | (pixels[offset] > pixels[offset + 1])
    return signature, sum(pixels) // len(pixels)


def similar_frames(signatures, other_signatures):
    if not signatures or not other_signatures:
        return False
    return sum(any((sig ^ other).bit_count() <= 4 and abs(tone - level) <= 10
                   for other, level in other_signatures)
               for sig, tone in signatures) >= 2


def prepare_source(path, source, accepted):
    if not source.get("page_url"):
        raise ValueError("원본 출처 페이지가 없습니다")
    if any(row["sha256"] == source["sha256"] or row["page_url"] == source["page_url"]
           for row in accepted):
        raise ValueError("원본 파일 또는 출처가 중복됩니다")
    start = select_start(path, source["duration_sec"], optimize_motion=True)
    metrics = motion(path, start, 6)
    if metrics["peak_change"] < 0.8:
        raise ValueError("SOURCE_LOW_MOTION")
    signatures = [frame_signature(path, start + offset) for offset in (1, 3, 5)]
    for row in accepted:
        if similar_frames(signatures, row.get("frame_signatures")):
            raise ValueError("대표 프레임의 시각적 중복이 의심됩니다")
    source.update(cut_start_sec=start, cut_duration_sec=6, frame_signatures=signatures,
                  source_motion=metrics)


def render_parts(work, title, source_dir, sources, captions, preset):
    parts = []
    for index, (source, caption) in enumerate(zip(sources, captions, strict=True)):
        plate = work / f"overlay_{index}.png"
        part = work / f"rank_{index}.mp4"
        overlay(plate, title, 5 - index, caption)
        vf = ("[0:v]split[bg][fg];"
              "[bg]scale=360:640:force_original_aspect_ratio=increase,crop=360:640,"
              "boxblur=12:2,scale=1080:1920,setsar=1[blur];"
              "[fg]scale=1080:1030:force_original_aspect_ratio=decrease:force_divisible_by=2[subject];"
              "[blur][subject]overlay=(W-w)/2:860-h/2[scene];"
              "[scene][1:v]overlay,setsar=1,fps=24,format=yuv420p[v]")
        run(FFMPEG + ["-v", "error", "-y", "-ss", str(source["cut_start_sec"]),
                      "-i", str(source_dir / source["file"]), "-i", str(plate),
                      "-filter_complex_threads", "2", "-filter_complex", vf, "-map", "[v]",
                      "-t", "6", "-an", "-c:v", "libx264", "-threads", "4",
                      "-preset", preset, "-crf", "23", str(part)])
        parts.append(part)
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{part.name}'\n" for part in parts), encoding="ascii")
    return listing


def mux(listing, target, gain):
    soundtrack = listing.parent / "soundtrack.wav"
    create_soundtrack(soundtrack, cue_times=CUE_TIMES, action_accents=False)
    run(FFMPEG + ["-v", "error", "-y", "-f", "concat", "-i", str(listing), "-i", str(soundtrack),
                  "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                  "-af", f"volume={gain}dB,alimiter=limit=0.79:level=false,"
                         "afade=t=in:d=0.25,afade=t=out:st=29.25:d=0.75",
                  "-movflags", "+faststart", str(target)])


def verify_media(video, observations=None):
    """Check the actual MP4, including a complete decode of both streams."""
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        timeout=30))
    videos = [stream for stream in data["streams"] if stream["codec_type"] == "video"]
    audios = [stream for stream in data["streams"] if stream["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        return {"format": False, "full_decode": False, "audio": False, "black": False}
    v, a = videos[0], audios[0]
    log = media_check(["-xerror", "-i", str(video), "-map", "0:v:0", "-map", "0:a:0",
                       "-vf", "crop=820:860:130:430,scale=160:-2,blackdetect=d=0.04:pix_th=0.08",
                       "-af", "silencedetect=noise=-42dB:d=0.7,volumedetect", "-f", "null", "-"])
    peak = re.search(r"max_volume: (-?[\d.]+) dB", log)
    if observations is not None:
        observations.update(peak_db=float(peak[1]) if peak else None,
                            black_times_sec=[float(t) for t in re.findall(r"black_start:([\d.]+)", log)],
                            silence_detected="silence_start:" in log)
    return {"format": (v["width"], v["height"], v["codec_name"], a["codec_name"]) ==
            (1080, 1920, "h264", "aac") and
            str(v.get("nb_frames")) == "720" and
            all(29.90 <= float(stream.get("duration", 0)) <= 30.15 for stream in (v, a)),
            "full_decode": True, "audio": bool(peak and -23 <= float(peak[1]) <= -1
                                                and "silence_start:" not in log),
            "black": "black_start:" not in log}


def write_report(out, report):
    save(out / REPORT, report)
    checks = report["technical_checks"]
    lines = ["# TOP5 제작 검수", "", f"- 주제 · {report['topic']}",
             f"- 기술 검수 · {'통과' if report['file'] else '실패'}",
             f"- MP4 · {report['file'] or '없음'}",
             f"- 편집 총점 · {report['editorial_score'] if report['editorial_score'] is not None else '미검증 (UNVERIFIED)'}",
             f"- 편집 판정 · {report['editorial_status']}",
             f"- 권리 판정 · {report['rights_status']}",
             f"- 게시 판정 · {report['publication_status']}",
             "- 휴대폰에서 GitHub에 로그인한 뒤 Actions 실행의 Artifacts에서 ZIP을 내려받으세요.",
             "", "| 평가 항목 | 배점 | 결과 |", "|---|---:|---|"]
    for name, row in zip(LABELS, report["scorecard"].values(), strict=True):
        value = row["score"] if row["score"] is not None else "미검증"
        lines.append(f"| {name} | {row['max']} | {value} |")
    if checks:
        lines.extend(["", f"기술 검사 결과 · `{json.dumps(checks, ensure_ascii=False)}`"])
    for attempt in report["attempts"]:
        failures = ", ".join(attempt["failed_checks"]) or "통과"
        lines.append(f"- 시도 {attempt['attempt']} · {failures}")
        for repair in attempt.get("repairs", []):
            lines.append(f"  - {repair['code']} · {repair['before']} → {repair['after']}")
    if report.get("topic_attempts"):
        lines.extend(["", "원본 확보 기록", ""])
        lines.extend(f"- {item['topic']} · {item['downloaded_valid_sources']}/5"
                     for item in report["topic_attempts"])
    if report.get("failure"):
        lines.extend(["", f"실패 원인 · {report['failure']}"])
    (out / "QA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_independent_review(report, final, sources, qa, rights):
    expected = {(source["page_url"], source["sha256"]) for source in sources}
    actual = {(entry.get("source_page"), entry.get("source_sha256"))
              for entry in rights.get("source_evidence", []) if isinstance(entry, dict)}
    if expected != actual or rights.get("video_sha256") != report["sha256"]:
        rights = {}
    result = evaluate(qa, rights, final)
    if result["rights_gate_passed"]:
        report.update(rights_status="RIGHTS_REVIEWED", rights_verified=True)
    if result["score_verified"]:
        total = result["score"]
        report["editorial_score"] = total
        for key, score in qa["editorial_scores"].items():
            report["scorecard"][key].update(status="VERIFIED", score=score)
        status = ("REVISE" if total < 75 else "ADDITIONAL_REVIEW" if total < 85
                  else "REVIEW_CANDIDATE" if result["publication_candidate_85"] else "RIGHTS_UNVERIFIED")
        report.update(editorial_status=status, status=status)
        if status == "REVIEW_CANDIDATE":
            report["publication_status"] = status


def source_issue(row, directory, selected, peers):
    path = directory / row["file"]
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        return "SOURCE_INTEGRITY"
    metadata = row.get("tags") or row.get("title") or ""
    query = row.get("query")
    if obvious_topic_mismatch(metadata, selected["topic"]) or (
            query and (query not in selected.get("search_queries", []) or
                       not topic_metadata_match(metadata, [query]))):
        return "SOURCE_TOPIC_MISMATCH"
    if any(row["sha256"] == other["sha256"] or row.get("page_url") == other.get("page_url") or
           similar_frames(row.get("frame_signatures"), other.get("frame_signatures")) for other in peers):
        return "SOURCE_DUPLICATE"
    if row.get("source_motion", {}).get("peak_change", 1) < 0.8:
        return "SOURCE_LOW_MOTION"
    if not 0 <= row["cut_start_sec"] <= row["duration_sec"] - 6 + 0.001:
        return "CUT_DURATION"
    return None


def replacement(sources, index, reserves, source_dir, selected, required=None):
    peers = sources[:index] + sources[index+1:]
    creators = Counter(row.get("creator") for row in peers)
    for row in reserves:
        if (required is None or row["sha256"] == required) and creators[row.get("creator")] < 2:
            if not source_issue(row, source_dir, selected, peers):
                return row
    return None


def timeline(sources, selected):
    return [{"rank": 5 - i, "output_start_sec": i * 6, "output_end_sec": (i + 1) * 6,
             "source_id": row.get("id"), "source_sha256": row["sha256"],
             "source_url": row.get("page_url"), "source_start_sec": row["cut_start_sec"],
             "source_end_sec": round(row["cut_start_sec"] + 6, 3), "motion": row.get("source_motion"),
             "topic_metadata": "MATCHED" if row.get("query") in selected.get("search_queries", [])
             else "UNVERIFIED", "topic_visual": "UNVERIFIED"}
            for i, row in enumerate(sources)]


def editorial_replacements(sources, reserves, qa, source_dir, selected, attempt):
    """Use only independently reviewed replacements available in the current reserve."""
    expected = {5 - i: (row["sha256"], row["cut_start_sec"], row["page_url"])
                for i, row in enumerate(sources)}
    verified = {clip.get("rank"): (clip.get("source_sha256"), clip.get("source_start_sec"),
                                  clip.get("source_page")) for clip in qa.get("clips", [])}
    if expected != verified:
        return None
    pool = [entry for entry in qa.get("replacement_candidates", [])
            if any((entry.get("source_sha256"), entry.get("source_page"), entry.get("source_start_sec"))
                   == (row["sha256"], row.get("page_url"), row["cut_start_sec"]) for row in reserves)]
    decision = plan_remediation(qa, pool, previous_attempts=attempt)
    if decision["status"] != "READY_FOR_REBUILD":
        return None
    revised = sources.copy()
    repairs = []
    for change in decision["repairs"]:
        index = 5 - change["rank"]
        entry = next(item for item in pool if item["source_page"] == change["to"])
        row = replacement(revised, index, reserves, source_dir, selected, required=entry["source_sha256"])
        if row is None:
            return None
        repairs.append({"code": "VERIFIED_EDITORIAL_BELOW_75", "rank": change["rank"],
                        "before": revised[index]["sha256"], "after": row["sha256"]})
        revised[index] = dict(row)
    return revised, repairs


def produce(plan_path, source_dir, out, review_path=None, qa_path=None, rights_path=None):
    out.mkdir(parents=True, exist_ok=True)
    final = out / VIDEO
    final.unlink(missing_ok=True)
    selected = read(plan_path)["selected"]
    topic = selected["topic"]
    acquisition = read(source_dir / "SOURCE_DOWNLOAD_QA.json")
    sources = [dict(row) for row in acquisition["sources"]]
    reserves = acquisition.get("reserve_sources", [])
    report = {"topic": topic, "status": "TECHNICAL_FAILED", "file": None, "sha256": None,
              "editorial_score": None, "editorial_status": "EDITORIAL_UNVERIFIED",
              "rights_status": "RIGHTS_UNVERIFIED", "rights_verified": False,
              "publication_status": "PUBLICATION_BLOCKED", "publication_approved": False,
              "rankings_verified": False,
              "scorecard": {key: {"max": value, "status": "UNVERIFIED", "score": None}
                            for key, value in CATEGORIES.items()},
              "technical_checks": {}, "attempts": [], "reference_status": "TEXT_SPEC_ONLY",
              "topic_attempts": acquisition.get("topic_attempts", [])}
    try:
        if len(sources) != 5:
            raise ValueError("원본 5개가 필요합니다")
        reviewed = load_reviewed_captions(review_path, sources)
        captions = [row[1] for row in reviewed] if reviewed else ["장면 검수 필요"] * 5
        approved_names = [row[0] for row in reviewed] if reviewed else [""] * 5
        for source in sources:
            if "cut_start_sec" not in source:
                source["cut_start_sec"] = select_start(source_dir / source["file"], source["duration_sec"])
        max_repairs = min(3, max(0, int(os.environ.get("TOP5_MAX_REPAIRS", "3"))))
        qa = read(Path(qa_path)) if qa_path else {}
        rights = read(Path(rights_path)) if rights_path else {}
        with TemporaryDirectory(dir=out) as tmp:
            work = Path(tmp)
            listing = None
            previous = ()
            gain = 4
            edited = False
            attempted_starts = [{row["cut_start_sec"]} for row in sources]
            for attempt in range(max_repairs + 1):
                target = work / "candidate.mp4"
                repairs = []
                observations = {}
                render_failure = None
                issues = [(i, issue) for i, row in enumerate(sources)
                          if (issue := source_issue(row, source_dir, selected, sources[:i]))]
                if issues:
                    checks = {code: False for i, code in issues}
                else:
                    try:
                        if listing is None:
                            listing = render_parts(work, topic.removesuffix(" TOP5"), source_dir,
                                                   sources, captions, "ultrafast" if attempt else "veryfast")
                        mux(listing, target, gain)
                        checks = verify_media(target, observations)
                        if all(checks.values()):
                            audio = soundtrack_checks(target, work)
                            overlays = overlay_checks(target, work, work / "frames")
                            hook = motion(target, 1, 2.125, "crop=820:700:130:500,")
                            checks.update({key: audio[key] for key in ("bgm", "transition_sfx")})
                            checks.update({key: overlays[key] for key in
                                           ("overlay_header", "rank_alignment", "caption_safe_area")})
                            checks["hook_motion"] = hook["sample_count"] >= 8 and hook["peak_change"] >= 0.8
                            observations.update(soundtrack=audio, overlay_frames=overlays["frames"], hook_1_to_3_sec=hook)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        render_failure = "RENDER_OR_DECODE"
                        checks = {render_failure: False}
                    except LayoutError:
                        render_failure = "CAPTION_LAYOUT"
                        checks = {render_failure: False}

                report["technical_checks"] = checks
                failures = tuple(key for key, passed in checks.items() if not passed)
                entry = {"attempt": attempt + 1, "failed_checks": failures, "gain_db": gain,
                         "timeline": timeline(sources, selected), "observations": observations, "repairs": repairs}
                report["attempts"].append(entry)
                if not failures:
                    editorial = evaluate(qa, {}, target)
                    if editorial["score_verified"] and editorial["score"] < 75:
                        correction = editorial_replacements(sources, reserves, qa, source_dir, selected, attempt)
                        report["prior_verified_score"] = editorial["score"]
                        if correction and attempt < max_repairs:
                            sources, changes = correction
                            repairs.extend(changes)
                            for change in changes:
                                index = 5 - change["rank"]
                                captions[index], approved_names[index] = "장면 검수 필요", ""
                                attempted_starts[index] = {sources[index]["cut_start_sec"]}
                            listing = None
                            edited = True
                            continue
                        report["failure"] = "검증 점수 75점 미만 · 검수된 대체 원본 부족 또는 수정 한도 도달"
                        report["editorial_status"] = "REVISE"
                        report["status"] = "PUBLICATION_BLOCKED"
                        break
                    target.replace(final)
                    frame_dir = out / "FRAME_REVIEW"
                    frame_dir.mkdir(exist_ok=True)
                    for artifact in (work / "frames").iterdir():
                        artifact.replace(frame_dir / artifact.name)
                    frames_manifest = frame_dir / "FRAME_REVIEW_MANIFEST.json"
                    frames = read(frames_manifest)
                    frames["video"] = VIDEO
                    for frame_metadata in frames["frames"]:
                        frame_metadata["path"] = str(frame_dir / frame_metadata["file"])
                    save(frames_manifest, frames)
                    report.update(file=VIDEO, sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
                                  status="EDITORIAL_UNVERIFIED", timeline=entry["timeline"],
                                  observations=observations, rankings_verified=False)
                    if edited:
                        report["editorial_recheck"] = "UNVERIFIED_NEW_VIDEO"
                    elif qa or rights:
                        apply_independent_review(report, final, sources, qa, rights)
                    break
                if attempt == max_repairs:
                    break

                for index, code in issues:
                    row = replacement(sources, index, reserves, source_dir, selected)
                    if row is not None:
                        repairs.append({"code": code, "rank": 5 - index,
                                        "before": sources[index]["sha256"], "after": row["sha256"]})
                        sources[index] = dict(row)
                        captions[index], approved_names[index] = "장면 검수 필요", ""
                        attempted_starts[index] = {row["cut_start_sec"]}
                if issues:
                    if not repairs:
                        break
                    listing = None
                    edited = True
                    continue

                if "black" in failures or "hook_motion" in failures or "format" in failures:
                    indices = {min(4, int(t // 6)) for t in observations.get("black_times_sec", [])}
                    if "hook_motion" in failures:
                        indices.add(0)
                    if "format" in failures:
                        indices.update(range(5))
                    for index in sorted(indices):
                        source = sources[index]
                        before = source["cut_start_sec"]
                        code = ("BLACK_TRANSITION" if "black" in failures else
                                "HOOK_LOW_MOTION" if "hook_motion" in failures else "CUT_DURATION")
                        try:
                            start = select_start(source_dir / source["file"], source["duration_sec"],
                                                 optimize_motion=True, skip=attempted_starts[index])
                        except ValueError:
                            row = replacement(sources, index, reserves, source_dir, selected)
                            if row is not None:
                                repairs.append({"code": code, "rank": 5 - index,
                                                "before": source["sha256"], "after": row["sha256"]})
                                sources[index] = dict(row)
                                captions[index], approved_names[index] = "장면 검수 필요", ""
                                attempted_starts[index] = {row["cut_start_sec"]}
                        else:
                            source["cut_start_sec"] = start
                            source["source_motion"] = motion(source_dir / source["file"], start, 6)
                            source["frame_signatures"] = [frame_signature(source_dir / source["file"], start + t)
                                                          for t in (1, 3, 5)]
                            attempted_starts[index].add(start)
                            repairs.append({"code": code, "rank": 5 - index, "before": before, "after": start})
                    listing = None
                if any(code in failures for code in ("audio", "bgm", "transition_sfx")) and failures != previous:
                    before = gain
                    peak = observations.get("peak_db")
                    gain += -3 if peak is not None and peak > -1 else 3
                    repairs.append({"code": "AUDIO_REMIX", "before": before, "after": gain})
                if (render_failure == "CAPTION_LAYOUT" or "caption_safe_area" in failures) and any(approved_names):
                    repairs.append({"code": "CAPTION_REGENERATED", "before": captions.copy(),
                                    "after": "장면 검수 필요"})
                    captions = ["장면 검수 필요"] * 5
                    approved_names = [""] * 5
                    listing = None
                if (render_failure == "RENDER_OR_DECODE" or "rank_alignment" in failures or
                        "overlay_header" in failures) and failures != previous:
                    repairs.append({"code": "TIMELINE_RERENDER", "before": "veryfast", "after": "ultrafast"})
                    listing = None
                if not repairs:
                    break
                previous = failures
                edited = True
        report.update(captions=captions, rank_names=approved_names, human_caption_reviewed=all(approved_names),
                      caption_method="human_reviewed_source_matched" if all(approved_names) else "review_placeholder")
        if not report["file"] and "failure" not in report:
            report["failure"] = "재검수 후 기술 오류 · " + ", ".join(failures)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        report["failure"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    save(out / "RIGHTS_EVIDENCE.json", {"status": report["rights_status"], "sources": sources,
                                       "video_sha256": report["sha256"],
                                       "audio": "프로젝트 내 합성 음악 및 효과음",
                                       "reused_content_status": "REVIEWED" if report["rights_verified"] else "UNVERIFIED"})
    write_report(out, report)
    if not report["file"]:
        raise SystemExit(report["failure"])
    return report
