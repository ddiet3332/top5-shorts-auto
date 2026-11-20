"""Bounded, keyless topic discovery from Commons and review-only TOP5 rendering."""
import argparse
from collections import Counter
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re
import subprocess
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import cv2
import numpy as np

from top5_auto_v29 import CUT_LENGTHS, assemble_video, save_license_and_status, technical_qa
from top5_hook_selection import SourceShortage, choose_hook, sampled_frames
from top5_public_video_discovery import commons

MAX_DOWNLOADS = 18
MAX_BYTES = 60 * 1024 * 1024
MAX_RESULTS = 60
UA = "TOP5-Shorts-Research/1.0 (https://github.com/ddiet3332/top5-shorts-auto)"
TOPICS = {
    "dog_surprises": ("강아지 행동", "dog", r"dogs?|doggy|pupp(?:y|ies)|retrievers?|labradors?|labradoodles?|collies?|poodles?|terriers?", (
        ("jump", "jumping", r"jump\w*|leap\w*", "도약"),
        ("dig", "digging", r"dig\w*", "땅 파기"),
        ("fetch", "fetch*", r"fetch\w*|retriev(?:e|es|ed|ing)", "물어 오기"),
        ("swim", "swim*", r"swim\w*|schwimm\w*", "헤엄"),
        ("roll", "rolling", r"roll\w*", "구르기"),
        ("shake", "shaking", r"shak\w*", "몸 흔들기"),
        ("catch", "catching", r"catch\w*|caught", "받아내기"),
        ("run", "running", r"runn\w*|sprint\w*", "달리기"),
    )),
    "bird_actions": ("새의 행동", "bird", r"birds?|parrots?|pigeons?|ducks?|crows?|sparrows?|robins?|eagles?|gulls?|herons?|finches?|mallards?", (
        ("fly", "flight", r"fl(?:y|ying|ies|ew|ight)", "날기"),
        ("feed", "feeding", r"feed\w*|eat\w*", "먹이 먹기"),
        ("bathe", "bathing", r"bath\w*", "목욕"),
        ("nest", "nest building", r"(?:build\w*.*nest|nest.*build\w*)", "둥지 짓기"),
        ("swim", "swimming", r"swim\w*", "헤엄"),
        ("land", "landing", r"land(?:ing|s|ed)", "착지"),
        ("preen", "preening", r"preen\w*", "깃털 손질"),
    )),
}


class Provider(Protocol):
    name: str
    def search(self, query: str) -> list[dict]: ...
    def download(self, item: dict, path: Path) -> int: ...


def trusted(url, host):
    parsed = urlsplit(url or "")
    return parsed.scheme == "https" and parsed.netloc == host


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CommonsProvider:
    name = "wikimedia_commons"

    def search(self, query):
        def fetch(url):
            with build_opener(NoRedirect()).open(Request(url, headers={"User-Agent": UA}), timeout=15) as response:
                data = json.loads(response.read(2 * 1024 * 1024))
            if "error" in data:
                raise ValueError("PROVIDER_API_ERROR")
            pages = data.get("query", {}).get("pages", {})
            if pages:
                data["query"]["pages"] = dict(sorted(pages.items(), key=lambda entry: entry[1].get("index", 0)))
            return data
        return commons(query, fetch)[:20]

    def download(self, item, path):
        if not trusted(item["file_url"], "upload.wikimedia.org"):
            raise ValueError("UNTRUSTED_MEDIA_HOST")
        with build_opener(NoRedirect()).open(Request(item["file_url"], headers={"User-Agent": UA}),
                                             timeout=15) as response, path.open("wb") as stream:
            if not response.headers.get_content_type().startswith(("video/", "application/octet-stream")):
                raise ValueError("NON_VIDEO_RESPONSE")
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("DOWNLOAD_BYTE_LIMIT")
                stream.write(chunk)
        return size


def error_code(exc):
    if isinstance(exc, HTTPError):
        return f"HTTP_{exc.code}"
    if isinstance(exc, ValueError) and re.fullmatch("[A-Z_]+", str(exc)):
        return str(exc)
    if isinstance(exc, subprocess.CalledProcessError):
        return "MEDIA_COMMAND_FAILED"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "MEDIA_COMMAND_TIMEOUT"
    return type(exc).__name__


def license_obligation(row):
    url = urlsplit(row.get("license_url") or "")
    if url.scheme not in {"http", "https"} or url.netloc not in {"creativecommons.org", "www.creativecommons.org"}:
        raise ValueError("LICENSE_LINK_UNSUPPORTED")
    path = url.path.strip("/").split("/")
    if path[:2] == ["publicdomain", "zero"] and len(path) >= 3:
        return "CC0 dedication; third-party rights UNVERIFIED"
    if len(path) >= 3 and path[0] == "licenses" and path[1] in {"by", "by-sa"}:
        return ("Attribute creator, link the license, indicate edits; " +
                ("adaptation subject to share-alike" if path[1] == "by-sa" else "third-party rights UNVERIFIED"))
    raise ValueError("LICENSE_LINK_UNSUPPORTED")


def inspect_media(path, record):
    metadata = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height:format=duration", "-of", "json", str(path),
    ], timeout=20))
    streams = metadata.get("streams", [])
    if not streams:
        raise ValueError("NO_VIDEO_STREAM")
    width, height = streams[0]["width"], streams[0]["height"]
    duration = float(metadata["format"]["duration"])
    record.update(width=width, height=height, duration_sec=duration)
    seconds = max(CUT_LENGTHS.values())
    if not seconds + .25 <= duration <= 180:
        raise ValueError("SOURCE_WINDOW_UNSUPPORTED")
    if min(width, height) < 240:
        raise ValueError("SOURCE_RESOLUTION_TOO_SMALL")
    starts = [round(x, 3) for x in np.linspace(0, min(duration-seconds-.2, 45), 3)]
    windows = []
    for start in dict.fromkeys(starts):
        frames = sampled_frames({"local_path": str(path)}, start, seconds)
        if len(frames) < 3 * seconds:
            continue
        pair_scores = []
        for a, b in zip(frames, frames[1:]):
            shift, confidence = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32))
            if confidence > .2 and np.linalg.norm(shift) > 2:
                pair_scores.append((0., 0.))
                continue
            mask = (np.abs(a-b) >= 25).astype(np.uint8)
            n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
            areas = [tuple(x) for x in stats[1:n] if 16 <= x[4] <= 850]
            region = max(areas, key=lambda x:x[4], default=(0, 0, 0, 0, 0))
            pair_scores.append((float(np.abs(a-b).mean()), min(810, width*1320/height)
                                *region[2]/64/3))
        motion = float(np.median([p[0] for p in pair_scores]))
        footprint = float(np.percentile([p[1] for p in pair_scores], 80))
        # Prefer sustained activity and keep two seconds around the strongest sampled motion.
        strongest = int(np.argmax([p[0] if p[1] >= 26 else 0 for p in pair_scores]))
        windows.append((motion, footprint, start, start+(strongest+1)/3, frames))
    record["sampled_windows"] = [
        {"start_sec": s, "end_sec": s+seconds, "peak_motion_sec": round(p,3),
         "frame_sample_times_sec":[round(s+i/3,3) for i in range(3*seconds)],
         "motion_proxy": round(m,3), "moving_region_width_phone_px": round(f,1)}
        for m,f,s,p,_ in windows
    ]
    if not windows:
        raise ValueError("NO_FULL_DECODED_WINDOW")
    record["decoded"] = True
    usable = [w for w in windows if w[0] >= 1.0 and w[1] >= 26]
    if not usable:
        raise ValueError("LOW_MOTION_OR_SMALL_MOVING_REGION")
    return max(usable, key=lambda w:(w[0],w[1]))


def run(topic_id, output, providers=None):
    headline, noun, subject, actions = TOPICS[topic_id]
    providers = [CommonsProvider()] if providers is None else providers
    output.mkdir(parents=True, exist_ok=True)
    originals = output/"originals"
    originals.mkdir(exist_ok=True)
    report = {"topic":topic_id, "searches":[], "candidates":[], "selected":[],
              "status":"SOURCE_SHORTAGE", "publication_approved":False,
              "rights":"UNVERIFIED", "audio_listening":"UNVERIFIED",
              "editorial_evidence":"Source-title action and moving-region proxies; semantic action and humor UNVERIFIED"}
    records, candidates, seen = [], [], set()
    for provider in providers:
        for _, phrase, _, _ in actions:
            query = f'{noun} {phrase}'
            attempt = {"provider":provider.name,"query":query,"returned":0}
            report["searches"].append(attempt)
            try:
                rows = provider.search(query)
                attempt["returned"] = len(rows)
            except (OSError, ValueError) as exc:
                attempt["error"] = error_code(exc)
                continue
            records.append([(provider,row,query) for row in rows])
    # Round-robin across queries so the first action cannot consume the whole budget.
    pooled = []
    for batch in zip_longest(*records):
        for item in batch:
            if item is None:
                continue
            provider, row, _ = item
            key = (provider.name, row["id"])
            if key not in seen and len(pooled) < MAX_RESULTS:
                seen.add(key)
                pooled.append(item)
    records = pooled
    hashes, images, downloads = set(), [], 0
    for provider,row,query in records:
        record = {k:row.get(k) for k in ("id","title","page_url","file_url","artist","license","license_url")}
        record.update(provider=provider.name, query=query)
        report["candidates"].append(record)
        path = originals/f"{len(report['candidates']):02}.video"
        try:
            if downloads >= MAX_DOWNLOADS:
                raise ValueError("DOWNLOAD_COUNT_LIMIT")
            if not row.get("mime","").startswith("video/") or not row.get("artist") or not row.get("page_url"):
                raise ValueError("MISSING_SOURCE_METADATA")
            record["license_obligation"] = license_obligation(row)
            if row.get("bytes") and row["bytes"] > MAX_BYTES:
                raise ValueError("DOWNLOAD_BYTE_LIMIT")
            title = re.sub(r"^File:|\.[a-z0-9]{2,5}$","",row["title"],flags=re.I)
            if re.search(r"\b(?:animation|cartoon|compilation|trailer|robot|documentary|military|attack\w*|bodycam|police|shooting|tetris)\b",title,re.I):
                raise ValueError("UNSUITABLE_TITLE")
            if not re.search(r"\b(?:"+subject+r")\b",title,re.I):
                raise ValueError("TOPIC_NOT_CORROBORATED_BY_TITLE")
            matches = [(family,label) for family,_,pattern,label in actions
                       if re.search(r"\b(?:"+pattern+r")\b",title,re.I)]
            downloads += 1
            record["downloaded_bytes"] = provider.download(row,path)
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream,"sha256").hexdigest()
            record["sha256"] = digest
            if digest in hashes:
                raise ValueError("DUPLICATE_BYTES")
            hashes.add(digest)
            motion, footprint, start, peak, frames = inspect_media(path,record)
            if any((np.abs(frames[:,None]-prior[None,:]).mean(axis=(2,3)).min(axis=1)<6).mean() >= .67
                   for prior in images):
                raise ValueError("VISUAL_DUPLICATE")
            images.append(frames)
            record["unique"] = True
            if len(matches) != 1:
                raise ValueError("ACTION_FAMILY_NEEDS_EDITORIAL_REVIEW")
            family,label = matches[0]
            record.update(action_family=family, disposition="HEURISTIC_CANDIDATE")
            candidates.append({**record, "record":record, "source_page":row["page_url"],
                               "author":row["artist"], "local_path":str(path),
                               "cut_start":start,"motion_proxy":motion,
                               "peak_motion_sec":peak,"hook_start":max(start,peak-1),
                               "reviewed_hook_only":True,"clear_rank_rail":True,
                               "caption":f"원본 제목 · {label}"})
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            record["rejection"] = error_code(exc)
            path.unlink(missing_ok=True)
    families = {}
    for row in sorted(candidates,key=lambda c:-c["motion_proxy"]):
        if row["action_family"] in families:
            row["record"]["rejection"] = "REPEATED_ACTION_FAMILY"
        else:
            families[row["action_family"]] = row
    ordered = list(families.values())
    ranked = list(reversed(ordered[:5]))
    hook = None
    if len(ordered) < 6:
        report["reason"] = ("INSUFFICIENT_DISTINCT_ACTION_FAMILIES" if records else
                            "PROVIDER_SEARCH_FAILED" if all("error" in s for s in report["searches"])
                            else "NO_CANDIDATES_FROM_PROVIDER")
    else:
        for row, length in zip(ranked,CUT_LENGTHS.values(),strict=True):
            # Ensure the proxy peak is inside every assigned rank, including shorter ranks.
            row["cut_start"] = round(max(row["cut_start"],row["peak_motion_sec"]-length+.5),3)
        ranked[-1]["replay_offset_sec"] = max(0, ranked[-1]["peak_motion_sec"]-ranked[-1]["cut_start"]-1.5)
        if any(row["cut_start"]+length > row["duration_sec"]
               for row,length in zip(ranked,CUT_LENGTHS.values(),strict=True)):
            report.update(status="EDITORIAL_REVIEW_REQUIRED",reason="RANK_WINDOW_OUT_OF_BOUNDS")
        else:
            try:
                hook = choose_hook(ranked,ordered[5:],list(CUT_LENGTHS.values()),
                                   report.setdefault("hook_attempts", []))
            except SourceShortage as exc:
                report.update(status="EDITORIAL_REVIEW_REQUIRED",reason=exc.code)
    report["funnel"] = {
        "searched":len(report["searches"]), "returned":sum(s["returned"] for s in report["searches"]),
        "unique_metadata":len(records), "download_attempts":downloads,
        "downloaded":sum("downloaded_bytes" in r for r in report["candidates"]),
        "decoded":sum(bool(r.get("decoded")) for r in report["candidates"]),
        "unique_media":sum(bool(r.get("unique")) for r in report["candidates"]),
        "distinct_action_families":len(ordered),
        "rejected":dict(Counter(r["rejection"] for r in report["candidates"] if "rejection" in r)),
        "selected":5 if hook else 0,
    }
    if hook:
        report.update(status="EDITORIAL_REVIEW_REQUIRED",reason="RENDER_PENDING")
        report["selected"] = [
            {**{k:r[k] for k in ("source_page","sha256","action_family","cut_start","peak_motion_sec",
                                  "author","license","license_url","license_obligation")},
             "cut_end":round(r["cut_start"]+seconds,3)}
            for r, seconds in zip(ranked,CUT_LENGTHS.values(),strict=True)]
        report["hook"] = {k:hook[k] for k in ("source_page","sha256","hook_start")}
    evidence = output/"DISCOVERY_REPORT.json"
    def save():
        evidence.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    save()
    if hook:
        topic = {"topic_id":topic_id,"headline":headline,"video_subject":headline+" TOP5"}
        try:
            save_license_and_status(topic,ranked,[],[],output,hook)
            video = assemble_video(topic,ranked,output,hook,moving_ending=True,
                                   hook_caption=hook["caption"],hook_caption_y=1712,mobile_captions=True)
            qa = technical_qa(video,output,topic,ranked)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            report.update(reason="RENDER_OR_DECODE_FAILED", render_error=error_code(exc))
            save()
            raise
        report.update(reason="ACTION_AND_RIGHTS_REVIEW_PENDING", video=video.name, full_decode=qa["full_decode"])
        save()
    print(report["status"],report["reason"],json.dumps(report["funnel"]),flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic",choices=TOPICS,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    run(args.topic,args.output)


if __name__ == "__main__":
    main()
