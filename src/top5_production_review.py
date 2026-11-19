"""Render and independently check the general-topic mobile review package."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from top5_generic_v06_preview import load_reviewed_captions, overlay, run
from top5_publication_gate import CATEGORIES, evaluate
from top5_source_contact_sheet import frame
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


def select_start(path, duration):
    """Find a six-second cut without sustained black frames."""
    if duration < 6:
        raise ValueError("원본이 6초 미만입니다")
    for start in dict.fromkeys((0, round((duration - 6) / 2, 3), round(duration - 6, 3))):
        log = media_check(["-xerror", "-ss", str(start), "-i", str(path), "-t", "6",
                           "-vf", "scale=160:-2,blackdetect=d=0.20:pix_th=0.08",
                           "-an", "-f", "null", "-"])
        if "black_start:" not in log:
            return start
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


def prepare_source(path, source, accepted):
    if not source.get("page_url"):
        raise ValueError("원본 출처 페이지가 없습니다")
    if any(row["sha256"] == source["sha256"] or row["page_url"] == source["page_url"]
           for row in accepted):
        raise ValueError("원본 파일 또는 출처가 중복됩니다")
    start = select_start(path, source["duration_sec"])
    signatures = [frame_signature(path, start + offset) for offset in (1, 3, 5)]
    for row in accepted:
        matches = sum(any((sig ^ other).bit_count() <= 4 and abs(tone - level) <= 10
                          for other, level in row["frame_signatures"])
                      for sig, tone in signatures)
        if matches >= 2:
            raise ValueError("대표 프레임의 시각적 중복이 의심됩니다")
    source.update(cut_start_sec=start, cut_duration_sec=6, frame_signatures=signatures)


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
    create_soundtrack(soundtrack, cue_times=(6, 12, 18, 24), action_accents=False)
    run(FFMPEG + ["-v", "error", "-y", "-f", "concat", "-i", str(listing), "-i", str(soundtrack),
                  "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                  "-af", f"volume={gain}dB,alimiter=limit=0.79:level=false,"
                         "afade=t=in:d=0.25,afade=t=out:st=29.25:d=0.75",
                  "-movflags", "+faststart", str(target)])


def verify_media(video):
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
                       "-vf", "crop=820:860:130:430,scale=160:-2,blackdetect=d=0.20:pix_th=0.08",
                       "-af", "silencedetect=noise=-42dB:d=0.7,volumedetect", "-f", "null", "-"])
    peak = re.search(r"max_volume: (-?[\d.]+) dB", log)
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
             "- 휴대폰에서 GitHub에 로그인한 뒤 Actions 실행의 Artifacts에서 ZIP을 내려받으세요.",
             "", "| 평가 항목 | 배점 | 결과 |", "|---|---:|---|"]
    for name, row in zip(LABELS, report["scorecard"].values(), strict=True):
        value = row["score"] if row["score"] is not None else "미검증"
        lines.append(f"| {name} | {row['max']} | {value} |")
    if checks:
        lines.extend(["", f"기술 검사 결과 · `{json.dumps(checks, ensure_ascii=False)}`"])
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


def produce(plan_path, source_dir, out, review_path=None, qa_path=None, rights_path=None):
    out.mkdir(parents=True, exist_ok=True)
    final = out / VIDEO
    final.unlink(missing_ok=True)
    plan = read(plan_path)
    acquisition = read(source_dir / "SOURCE_DOWNLOAD_QA.json")
    sources = acquisition["sources"]
    topic = plan["selected"]["topic"]
    report = {"topic": topic, "status": "TECHNICAL_FAILED", "file": None, "sha256": None,
              "editorial_score": None, "editorial_status": "EDITORIAL_UNVERIFIED",
              "rights_status": "RIGHTS_UNVERIFIED", "rights_verified": False, "publication_approved": False,
              "rankings_verified": False,
              "scorecard": {key: {"max": value, "status": "UNVERIFIED", "score": None}
                            for key, value in CATEGORIES.items()},
              "technical_checks": {}, "attempts": [], "topic_attempts": acquisition.get("topic_attempts", [])}
    save(out / "RIGHTS_EVIDENCE.json", {"status": "RIGHTS_UNVERIFIED", "sources": sources,
                                       "audio": "프로젝트 내 합성 음악 및 효과음",
                                       "reused_content_status": "UNVERIFIED"})
    try:
        if len(sources) != 5 or len({row["sha256"] for row in sources}) != 5:
            raise ValueError("서로 다른 원본 5개가 필요합니다")
        reviewed = load_reviewed_captions(review_path, sources)
        captions = [row[1] for row in reviewed] if reviewed else ["장면 검수 필요"] * 5
        report.update(captions=captions, human_caption_reviewed=bool(reviewed),
                      rank_names=[row[0] for row in reviewed] if reviewed else [],
                      caption_method="human_reviewed_source_matched" if reviewed else "review_placeholder")
        for source in sources:
            if "cut_start_sec" not in source:
                source["cut_start_sec"] = select_start(source_dir / source["file"], source["duration_sec"])
        max_repairs = max(0, int(os.environ.get("TOP5_MAX_REPAIRS", "3")))
        with TemporaryDirectory(dir=out) as tmp:
            work = Path(tmp)
            listing = None
            previous = None
            gain = 4
            for attempt in range(max_repairs + 1):
                target = work / "candidate.mp4"
                try:
                    if listing is None:
                        listing = render_parts(work, topic.removesuffix(" TOP5"), source_dir,
                                               sources, captions, "veryfast" if not attempt else "ultrafast")
                    mux(listing, target, gain)
                    checks = verify_media(target)
                    failures = tuple(key for key, passed in checks.items() if not passed)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    checks = {"encode_or_decode": False}
                    failures = ("encode_or_decode",)
                    listing = None
                report["technical_checks"] = checks
                report["attempts"].append({"attempt": attempt + 1, "failed_checks": failures, "gain_db": gain})
                if not failures:
                    target.replace(final)
                    report.update(file=VIDEO, sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
                                  status="EDITORIAL_UNVERIFIED")
                    break
                if failures == previous:
                    break
                previous = failures
                if failures == ("audio",):
                    gain += 3
                elif failures != ("encode_or_decode",):
                    break
        if not report["file"]:
            report["failure"] = "재검수 후 기술 오류 · " + ", ".join(failures)
        elif qa_path or rights_path:
            apply_independent_review(report, final, sources,
                                     read(Path(qa_path)) if qa_path else {},
                                     read(Path(rights_path)) if rights_path else {})
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        report["failure"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    write_report(out, report)
    if not report["file"]:
        raise SystemExit(report["failure"])
    return report
