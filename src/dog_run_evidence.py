"""Validate a dog production run and write immutable, independently ordered evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

VIDEO = "TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
INVENTORY = "REVIEWED_SOURCE_SELECTION.json"
HOOK = "INDEPENDENT_HOOK_AUDIT.json"
MANIFEST = "PRODUCTION_RUN.json"
SHEET = "TOP5_CONTACT_SHEET.jpg"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(path)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_source_hashes(output, selected, hook):
    fields = ("source_page", "sha256", "action_family")
    if len(selected) != 5 or any(len({row[key] for row in selected}) != 5 for key in fields):
        raise ValueError("SOURCE_NOT_DISTINCT")
    if (hook.get("independent_hook") is not True or hook["sha256"] in {row["sha256"] for row in selected}
        or hook["source_page"] in {row["source_page"] for row in selected}):
        raise ValueError("HOOK_NOT_INDEPENDENT")
    for row in [*selected,hook]:
        match = re.fullmatch(r"https://www\.pexels\.com/video/[\w-]+-(\d+)/?", row["source_page"])
        if not match or digest(output/"originals"/f"PX-{match[1]}.mp4") != row["sha256"]:
            raise ValueError("SOURCE_HASH_MISMATCH")


def verify_streams(video):
    streams = json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_streams","-of","json",str(video)
    ], timeout=20))["streams"]
    if len(streams) != 2:
        raise ValueError("UNEXPECTED_STREAM_COUNT")
    picture,audio = streams
    if (picture["codec_name"],picture["width"],picture["height"],picture["avg_frame_rate"],
        picture["nb_frames"],audio["codec_name"]) != ("h264",1080,1920,"24/1","720","aac"):
        raise ValueError("UNEXPECTED_STREAM_FORMAT")
    if any(float(s["start_time"]) != 0 or float(s["duration"]) != 30 for s in streams):
        raise ValueError("UNEXPECTED_STREAM_DURATION")
    subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(video),
                    "-map","0:v:0","-map","0:a:0","-f","null","-"],check=True,timeout=150)


def contact_sheet(video, path):
    frames = (0,24,47,48,143,144,263,264,359,360,503,504,647,648,719)
    expr = "+".join(f"eq(n\\,{i})" for i in frames)
    subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(video),"-vf",
                    f"select={expr},scale=360:640,tile=5x3","-frames:v","1","-update","1",str(path)],
                   check=True,timeout=90)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("CONTACT_SHEET_MISSING")


def finalize(output, review, run_id, attempt, commit, install, render):
    inventory = read_json(output/INVENTORY) if (output/INVENTORY).is_file() else None
    video = output/VIDEO
    archive = review/"runs"/str(run_id)/f"attempt-{attempt}"
    archive.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id":run_id,"run_attempt":attempt,"source_commit":commit,
        "install_outcome":install,"render_outcome":render,
        "status":"MP4_NOT_CREATED","full_decode":"NOT_RUN_NO_MP4","contact_sheet":"NOT_RUN_NO_MP4",
        "video_sha256":None,"source_hashes_verified":False,"distinct_rank_sources":0,
        "publication_approved":False,"rights":"UNVERIFIED","audio_listening":"UNVERIFIED",
    }
    if inventory:
        write_json(archive/INVENTORY,inventory)
    if not video.is_file() or not video.stat().st_size:
        if install == "cancelled":
            report["reason"] = "INSTALL_CANCELLED"
        elif install != "success":
            report["reason"] = "INSTALL_INCOMPLETE"
        elif inventory and inventory.get("status") == "SOURCE_SHORTAGE":
            report.update(status="SOURCE_SHORTAGE",reason="INSUFFICIENT_REVIEWED_ORIGINALS")
        else:
            report["reason"] = "RENDER_DID_NOT_CREATE_MP4"
    elif install != "success" or render != "success":
        report.update(status="MP4_REJECTED",reason="RENDER_INCOMPLETE",
                      full_decode="NOT_RUN_RENDER_INCOMPLETE",contact_sheet="NOT_RUN_RENDER_INCOMPLETE")
    elif not all(shutil.which(tool) for tool in ("ffmpeg","ffprobe")):
        report.update(status="MP4_REJECTED",reason="FFMPEG_OR_FFPROBE_MISSING",
                      full_decode="NOT_RUN_TOOL_MISSING",contact_sheet="NOT_RUN_TOOL_MISSING")
    else:
        report.update(status="MP4_REJECTED",full_decode="NOT_RUN_SOURCE_VALIDATION",
                      contact_sheet="NOT_RUN_VALIDATION")
        try:
            if not inventory or inventory["status"] != "SELECTED":
                raise ValueError("SOURCE_INVENTORY_MISSING_OR_INCOMPLETE")
            hook = read_json(output/HOOK)
            verify_source_hashes(output,inventory["selected"],hook)
            video_hash = digest(video)
            if hook["rendered_video_sha256"] != video_hash:
                raise ValueError("RENDER_HASH_MISMATCH")
            report.update(source_hashes_verified=True,distinct_rank_sources=5,full_decode="FAILED")
            verify_streams(video)
            report.update(full_decode="PASS",contact_sheet="FAILED")
            contact_sheet(video,archive/SHEET)
        except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
            report["reason"] = (str(exc) if isinstance(exc,ValueError)
                                and re.fullmatch("[A-Z_]+",str(exc)) else type(exc).__name__)
        else:
            report.update(status="SUCCESS",video_sha256=video_hash,contact_sheet="PASS",
                          resolution="1080x1920",fps=24,frames=720,duration_sec=30,
                          video_codec="h264",audio_codec="aac")
            for name in (HOOK,"SOURCE_CREDITS_REVIEW.md","V32_ENDING_SOURCE.json"):
                if (output/name).is_file():
                    shutil.copyfile(output/name,archive/name)
    write_json(archive/MANIFEST,report)
    return archive,report


def record(archive, review):
    report = read_json(archive/MANIFEST)
    run_id, attempt = (int(report[key]) for key in ("run_id","run_attempt"))
    target = review/"runs"/str(run_id)/f"attempt-{attempt}"
    if target != archive:
        if target.exists():
            if (target/MANIFEST).read_bytes() != (archive/MANIFEST).read_bytes():
                raise ValueError("IMMUTABLE_ATTEMPT_CONFLICT")
        else:
            shutil.copytree(archive,target,ignore=shutil.ignore_patterns("*.jpg"))
    names = ["latest_attempt"]
    if (report["status"] == "SUCCESS" and report["full_decode"] == "PASS"
        and report["source_hashes_verified"] is True and report["distinct_rank_sources"] == 5
        and re.fullmatch("[a-f0-9]{64}",report["video_sha256"] or "")):
        names.append("latest_success")
    for name in names:
        pointer = review/name/MANIFEST
        previous = read_json(pointer) if pointer.is_file() else None
        if previous and (int(previous["run_id"]),int(previous["run_attempt"])) >= (run_id,attempt):
            continue
        write_json(pointer,{**report,"evidence_path":target.relative_to(review).as_posix()})


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command",required=True)
    collect = commands.add_parser("finalize")
    for key in ("output","review"):
        collect.add_argument(key,type=Path)
    for key in ("run_id","attempt"):
        collect.add_argument(key,type=int)
    for key in ("commit","install","render"):
        collect.add_argument(key)
    persist = commands.add_parser("record")
    for key in ("archive","review"):
        persist.add_argument(key,type=Path)
    args = vars(parser.parse_args())
    if args.pop("command") == "record":
        record(**args)
        return
    archive,report = finalize(**args)
    record(archive,args["review"])
    print(json.dumps(report,ensure_ascii=False))


if __name__ == "__main__":
    main()
