#!/usr/bin/env python3
"""V17 broad CC BY/CC0 Commons animal-action triage.

Discovers candidates from multiple phrases and categories, excludes known clips,
filters low-resolution and externally reuploaded material, then records a modest
number of real 5-second action previews. Scores are priority for HUMAN REVIEW,
not humor, safety, copyright approval or YouTube monetization quality.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

from top5 import (
    query_candidates, category_candidates, download_video,
    probe_duration, probe_dimensions
)
from v8_moments import window_candidates, moment_photo

SEARCHES=(
    "cat jumps", "funny cat", "cat opening door", "playing kittens",
    "cat climbing", "cat trick", "cat surprised", "cat and dog playing",
)
CATEGORIES=(
    "Videos of jumping cats", "Videos of playing cats", "Videos of cats",
    "Videos of kittens", "Videos of cats and mice"
)
BLOCK_EXTERNAL=r'(youtube|youtu\.be|tiktok|vimeo|instagram|facebook|dailymotion)'
CUE_WORDS={
    "leap":("jump","saut","salto","springt","leap","backflip","bounce"),
    "object":("box","bag","door","drawer","shelf","keyboard","piano","opening"),
    "chase":("chase","mouse","laser","catch","run","attack","follow"),
    "trick":("trick","training","climb","scramble","skate","acrobat"),
    "play":("playing","play","kitten","puppy","toy","game","fight")
}
# No semantic claim: 'jump' in metadata does not prove any jump is visible.
def action_group(title):
    lower=str(title).casefold()
    for group,words in CUE_WORDS.items():
        if any(word in lower for word in words):
            return group
    return "other"

def sufficient_resolution(w,h,minimum_short_edge=480,minimum_long_edge=720):
    return (isinstance(w,int) and isinstance(h,int) and
            min(w,h)>=minimum_short_edge and max(w,h)>=minimum_long_edge)

def is_external_reupload(item):
    source=str(item.get("source_claim",""))
    flags=" ".join(item.get("review_flags",[]))
    return (bool(re.search(BLOCK_EXTERNAL,source,re.IGNORECASE)) or
            "외부 재게시" in flags)

def editorial_priority(item):
    # Only a scheduling heuristic. Never infer comedic value or rights.
    title=item.get("title","").casefold()
    group=action_group(title)
    base={"leap":6,"object":5,"chase":5,"trick":4,"play":3,"other":0}[group]
    if re.search(r'(cat|kitten|feline|katz|gato)',title):
        base+=1
    if re.search(r'(dog|puppy|goat|fox)',title):
        base-=2
    source=str(item.get('source_claim','')).casefold()
    if "own work" in source or "자작" in source:
        base+=2
    if is_external_reupload(item):
        base-=20
    # Deliberately don't score a clip's actual laughter/virality.
    return base

def collect_sources(searches=SEARCHES,categories=CATEGORIES,max_pool=160):
    collected={}
    failures=[]
    searched=[]
    for kind,names in (("query",searches),("category",categories)):
        for phrase in names:
            try:
                results=(query_candidates(phrase,100) if kind=="query" else
                         category_candidates(phrase,100))
                new=0
                for cand in results:
                    key=cand["title"].casefold()
                    if key not in collected:
                        collected[key]=cand
                        new+=1
                searched.append({"type":kind,"term":phrase,"new":new})
                print(f"[V17 {kind}] {phrase}: {new} new, {len(collected)} total",flush=True)
            except Exception as err:
                # No need to kill a multi-source audit when one API query is unavailable.
                failures.append({"type":kind,"term":phrase,"error":type(err).__name__})
                print(f"[V17 unavailable] {kind} {phrase}: {type(err).__name__}",flush=True)
            if len(collected)>=max_pool:
                break
        if len(collected)>=max_pool:
            break
    return list(collected.values()), searched, failures

def archived_titles(base="sample"):
    old=set()
    for name in (
        "v12-mixed-selection.json","v13-mixed-selection.json",
        "v14-mixed-selection.json","v15-mixed-selection.json",
        "v16-mixed-selection.json"
    ):
        p=Path(base)/name
        if p.exists():
            for row in json.loads(p.read_text(encoding="utf-8")):
                if row.get("provider")=="wikimedia":
                    old.add(row.get("title","").casefold())
    return old

def render_preview(path,start,outfile,seconds=5.0):
    vf=("scale=540:960:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=540:960:(ow-iw)/2:(oh-ih)/2:color=black,fps=12,setsar=1")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-ss",f"{start:.2f}","-i",str(path),"-t",str(seconds),
        "-vf",vf,"-an","-c:v","libx264","-preset","veryfast",
        "-crf","30","-movflags","+faststart",str(outfile)],
        check=True,timeout=100,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def make_review(out,limit=10,byte_budget=115*1024*1024,max_file=30*1024*1024):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    preview_dir=out/"V17_PREVIEWS"
    preview_dir.mkdir(exist_ok=True)
    frames_dir=out/"V17_FRAMES"
    frames_dir.mkdir(exist_ok=True)
    candidates,queries,errors=collect_sources()
    used=archived_titles()
    report={"status":"NEEDS_MANUAL_REVIEW","automated_humor_rating":None,
            "license_review_complete":False,"approved_for_publication":False,
            "queries":queries,"query_errors":errors,"raw_license_filtered_pool":len(candidates),
            "previously_used_title_count":len(used),"rejected":[],"candidates":[]}
    candidates.sort(key=lambda x:(editorial_priority(x),-int(x.get("size_bytes",0))),reverse=True)
    selected=0
    bytes_read=0
    group_used={}
    for src in candidates:
        name=src["title"]
        group=action_group(name)
        if name.casefold() in used:
            report["rejected"].append({"title":name,"reason":"ALREADY_USED"})
            continue
        if is_external_reupload(src):
            report["rejected"].append({"title":name,"reason":"EXTERNAL_REUPLOAD_UNVERIFIED"})
            continue
        if int(src.get("size_bytes",0))>max_file:
            report["rejected"].append({"title":name,"reason":"DOWNLOAD_OVER_30MB"})
            continue
        if group_used.get(group,0)>=3:
            report["rejected"].append({"title":name,"reason":"DUPLICATE_ACTION_CATEGORY"})
            continue
        if group=="other" and selected>=max(3,limit//2):
            report["rejected"].append({"title":name,"reason":"NO_EXPLICIT_ACTION_IN_TITLE"})
            continue
        if bytes_read+int(src.get("size_bytes",0))>byte_budget:
            report["rejected"].append({"title":name,"reason":"SESSION_BYTES_CAP"})
            continue
        ext=Path(urllib.parse.urlsplit(src["download_url"]).path).suffix.lower()
        if ext not in (".webm",".mp4",".ogv",".ogg"):
            report["rejected"].append({"title":name,"reason":"UNSUPPORTED_FILETYPE"})
            continue
        local=preview_dir/f"temporary_{selected:02d}{ext}"
        entry={"title":name,"group":group,"source_page":src["source_page"],
               "author":src["author"],"license":src["license"],
               "license_url":src["license_url"],"source_claim":src["source_claim"],
               "review_flags":src["review_flags"],
               "priority_for_preview_only":editorial_priority(src),
               "individual_license_reviewed":False,
               "actual_comedic_payoff_verified":False,
               "source_audio_approved":False,
               "approved_for_publication":False,"moments":[]}
        try:
            download_video(src,local)
            bytes_read+=local.stat().st_size
            duration=probe_duration(local)
            w,h=probe_dimensions(local)
            entry.update({"duration_sec":round(duration,2),"width":w,"height":h})
            if not sufficient_resolution(w,h):
                entry["status"]="REJECT_LOW_RESOLUTION"
            elif not 5.4<=duration<=240:
                entry["status"]="REJECT_DURATION"
            else:
                windows=window_candidates(local,duration,seconds=5.0,count=2,max_scan=65)
                for ordinal,window in enumerate(windows,1):
                    start=float(window["start"])
                    if duration-start<5.0:
                        continue
                    output=preview_dir/f"V17_{selected+1:02d}_M{ordinal}.mp4"
                    still=frames_dir/f"V17_{selected+1:02d}_M{ordinal}.jpg"
                    render_preview(local,start,output)
                    moment_photo(local,min(start+2.5,duration-0.15),still)
                    entry["moments"].append({
                        "start_sec":start,"movement_score_not_funny_score":window["motion"],
                        "preview":str(output.relative_to(out)),
                        "frame":str(still.relative_to(out))})
                entry["status"]="VIDEO_PREVIEW_READY_NOT_APPROVED" if entry["moments"] else "REJECT_NO_PREVIEW"
        except Exception as exc:
            entry["status"]="FAILED_MEDIA_OR_DOWNLOAD"
            entry["error_type"]=type(exc).__name__
        finally:
            local.unlink(missing_ok=True)
        if entry["status"]=="VIDEO_PREVIEW_READY_NOT_APPROVED":
            report["candidates"].append(entry)
            group_used[group]=group_used.get(group,0)+1
            selected+=1
            print(f"[V17 audition] {selected}/{limit} {name} {entry['width']}x{entry['height']} / {entry['group']}",flush=True)
        else:
            report["rejected"].append({"title":name,"reason":entry["status"]})
            print(f"[V17 skipped] {name}: {entry['status']}",flush=True)
        if selected>=limit or bytes_read>=byte_budget:
            break
    report["audition_count"]=selected
    report["downloaded_bytes"]=bytes_read
    (out/"V17_CANDIDATE_AUDIT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    columns=("title","group","width","height","duration_sec","license","author",
             "source_page","status","priority_for_preview_only")
    with (out/"V17_REVIEW_QUEUE.csv").open("w",encoding="utf-8-sig",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=columns,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["candidates"])
    guide=[
        "# V17 행동 중심 검수 대기 목록","",
        f"기존 클립 제외 후 실제 영상 미리보기: **{selected}개**",
        f"위키미디어 CC BY/CC0 1차 메타데이터 통과 원본: **{len(candidates)}개**",
        "목표는 '재미있는 5개'를 검증하는 것이지 숫자 5를 무조건 채우는 게 아닙니다.",
        "‘움직임 점수’는 컷과 카메라 움직임에도 반응하므로 재미·웃음·반전을 뜻하지 않습니다.",
        "외부 YouTube·TikTok 재게시 파일은 저작자 권리가 미확인되어 우선 제외했습니다.",
        "최소 해상도 720×480 수준 이상, 클립 길이 5.4초 이상, 원본 30MB 이하.",
        "CC BY / CC0 메타데이터만 확인하며, 제3자 음원·초상·상표는 별도로 검토해야 합니다.",
        "실제 점프·사고·반전이 없으면 다음 쇼츠 장면으로 채택하면 안 됩니다.",
        ""
    ]
    for entry in report["candidates"]:
        guide.extend([f"## {entry['title']}",
            f"- 동작 카테고리: {entry['group']} (메타데이터 기반)",
            f"- 기술 해상도: {entry['width']} × {entry['height']}",
            f"- 라이선스 표기: {entry['license']} / 출처: {entry['source_page']}",
            f"- 미리보기: {', '.join(x['preview'] for x in entry['moments'])}",
            "- 영상 재미·실제 5초 행동: 사람의 재생 검수 필요",
            "- 승인 상태: 아니오",""])
    (out/"V17_EDITORIAL_QUEUE.md").write_text("\n".join(guide),encoding="utf-8")
    # Contact sheets use actual source frames, not generic web image illustrations.
    if selected:
        ordered=sorted(frames_dir.glob("V17_*_M1.jpg"))
        for i,frame in enumerate(ordered,1):
            (frames_dir/f"sheet_{i:02d}.jpg").write_bytes(frame.read_bytes())
        columns=3;rows=(len(ordered)+columns-1)//columns
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-framerate","1","-start_number","1",
                        "-i",str(frames_dir/"sheet_%02d.jpg"),
                        "-vf",f"tile={columns}x{rows}:padding=5:margin=6:color=black",
                        "-frames:v","1","-q:v","3",str(out/"V17_CONTACT_SHEET.jpg")],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=50)
    print(f"[V17 complete] {selected} actual previews, 0 human-approved or published",flush=True)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="output")
    p.add_argument("--limit",type=int,default=10)
    args=p.parse_args()
    if not 1<=args.limit<=12:
        raise ValueError("At most 12 video audits per job")
    make_review(args.output,limit=args.limit)

if __name__=="__main__":
    main()
