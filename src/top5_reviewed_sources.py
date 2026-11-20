"""Select and verify topic sources from an optional frame-reviewed catalog."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from top5_hook_selection import SourceShortage, sampled_frames
from v12_pexels_audition import download_single_pexels, safe_failure_code


def select_reviewed_sources(topic, output, rank_lengths):
    catalog = json.loads(Path(topic["source_catalog"]).read_text(encoding="utf-8"))
    if catalog["topic_id"] != topic["topic_id"]:
        raise ValueError("Source catalog topic mismatch")
    originals = output / "originals"
    originals.mkdir(exist_ok=True, parents=True)
    eligible, hooks, failures = [], [], []
    hashes, samples = set(), []
    for source in catalog["sources"]:
        path = originals / (source["id"] + ".mp4")
        try:
            info = download_single_pexels(source, path, max_bytes=125*1024*1024)
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            start, payoff = source["start_sec"], source["payoff_sec"]
            hook = source.get("independent_hook", False)
            length = 2 if hook else max(rank_lengths)
            if digest != source["sha256"]:
                raise ValueError("REVIEWED_BYTES_CHANGED")
            if not 0 <= start <= payoff < start+length <= info["duration_sec"]:
                raise ValueError("INVALID_SOURCE_WINDOW")
            width, height = map(int, subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=width,height", "-of", "csv=p=0", str(path),
            ], text=True, timeout=30).splitlines()[0].split(","))
            scale = min((1080 if hook else 810)/width, 1320/height)/3
            subject_w, subject_h = source["payoff_subject_fraction"]
            if not (0 < subject_w <= 1 and 0 < subject_h <= 1):
                raise ValueError("INVALID_SUBJECT_BOUNDS")
            span = max(subject_w*width, subject_h*height)*scale
            if span < 48:
                raise ValueError("SUBJECT_TOO_SMALL_AT_PAYOFF")
            row = {
                "title":source["title"], "source_page":source["page_url"],
                "author":source["creator"], "provider":"pexels",
                "license":source["license_label"], "license_url":source["license_url"],
                "local_path":str(path), "duration_sec":info["duration_sec"],
                "sha256":digest,
                "cut_start":start, "payoff_sec":payoff, "action_family":source["action_family"],
                "payoff_phone_px":round(span, 1),
                "editorial_quality_heuristic":source["payoff_priority"],
                "caption":source["caption"], "label":source["label"],
                "review_basis":source["observed_action"], "clear_rank_rail":True,
                "publication_approved":False, "rights_verified":False,
            }
            frames = sampled_frames(row, start, length)
            if len(frames) < int(length*3):
                raise ValueError("SHORT_DECODED_WINDOW")
            motion = float(np.abs(np.diff(frames, axis=0)).mean())
            if motion < 0.45:
                raise ValueError("LOW_DECODED_MOTION")
            if digest in hashes or any(
                (np.abs(frames[:,None]-prior[None,:]).mean(axis=(2,3)).min(axis=1) < 6).mean() >= .67
                for prior in samples
            ):
                raise ValueError("DUPLICATE_SOURCE")
            hashes.add(digest)
            samples.append(frames)
            row["motion_proxy"] = motion
            if hook:
                hooks.append({**row, "hook_start":start, "reviewed_hook_only":True})
            else:
                row["caption_sequence"] = source["caption_sequence"]
                if "replay_offset_sec" in source:
                    row["replay_offset_sec"] = source["replay_offset_sec"]
                eligible.append(row)
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else safe_failure_code(exc)
            failures.append({"id":source["id"],"source_page":source["page_url"],"reason":reason})
            path.unlink(missing_ok=True)
    families = {}
    for row in sorted(eligible, key=lambda x:(-x["editorial_quality_heuristic"], x["source_page"])):
        families.setdefault(row["action_family"], row)
    selected = list(reversed(list(families.values())[:len(rank_lengths)]))
    windows_ok = len(selected) == len(rank_lengths) and all(
        row["payoff_sec"] < row["cut_start"]+seconds
        for row,seconds in zip(selected,rank_lengths)
    )
    status = "SELECTED" if windows_ok and hooks else "SOURCE_SHORTAGE"
    audit = {"status":status,"topic":topic["topic_id"],"eligible_families":list(families),
             "rejections":failures,"rank_windows_verified":windows_ok,
             "hook_candidates":[row["source_page"] for row in hooks],
             "selected":[{k:row[k] for k in ("source_page","sha256","author","license","license_url",
                                             "cut_start","payoff_sec","action_family",
                                             "payoff_phone_px","review_basis")} for row in selected],
             "visibility_basis":"reviewed payoff bounding box projected into phone frame",
             "rights_verified":False,"publication_approved":False}
    (output/"REVIEWED_SOURCE_SELECTION.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if status != "SELECTED":
        raise SourceShortage(status,"Insufficient distinct reviewed ranks or independent hook",failures)
    return selected, failures, hooks
