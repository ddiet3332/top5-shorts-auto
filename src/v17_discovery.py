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
    "cat startled", "cat knocks object", "kitten fails jump",
    "cat chases tail", "cat startled by mirror", "cat in box",
    "cat playing with dog", "cat catches toy", "cat reacts to toy",
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
    "play":("playing","play","kitten","puppy","toy","game","fight"),
    "reaction":("discovers","surprised","surprise","spied","reacts","reaction",
                "unexpected","scared","afraid","startled","caught","curious")
}
# No semantic claim: 'jump' in metadata does not prove any jump is visible.
def action_group(title):
    lower=str(title).casefold()
    for group,words in CUE_WORDS.items():
        if any(word in lower for word in words):
            return group
    return "other"

def has_feline_title_evidence(title):
    """Conservative filename hint; never an actual visual verification."""
    name=str(title).casefold()
    return (bool(re.search(
        r'(?<![a-z])(cats?|kittens?|kitties|kitty|felines?|gatos?|gatas?|'
        r'katzen|katze|katz|neko|gatti|gatto)(?![a-z])',name))
        or "猫" in name)


def likely_cat_candidate(item):
    """Cat filename OR membership in a cat-specific Commons category.

    Matching a broad 'cat trick' text search alone is NOT animal evidence.
    """
    return (has_feline_title_evidence(item.get("title",""))
            or bool(item.get("cat_category_evidence",False)))


def sufficient_resolution(w,h,minimum_short_edge=480,minimum_long_edge=720):
    return (isinstance(w,int) and isinstance(h,int) and
            min(w,h)>=minimum_short_edge and max(w,h)>=minimum_long_edge)

def audition_seconds(duration):
    """Allow an honest 4-second moment, without padding it into fake 5 seconds."""
    if not 4.0<=duration<=240.0:
        return 0.0
    return round(min(5.0,duration-0.2),2)


def is_external_reupload(item):
    source=str(item.get("source_claim",""))
    flags=" ".join(item.get("review_flags",[]))
    return (bool(re.search(BLOCK_EXTERNAL,source,re.IGNORECASE)) or
            "외부 재게시" in flags)

def editorial_priority(item):
    # Only a scheduling heuristic. Never infer comedic value or rights.
    title=item.get("title","").casefold()
    group=action_group(title)
    base={"leap":6,"object":5,"chase":5,"reaction":5,"trick":4,"play":3,"other":1}[group]
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
    """Sample every search/category before capping the pool.

    The previous implementation could hit the 160-item cap after two queries,
    never reaching later action searches or the curated categories. Alternating
    between search buckets preserves source diversity, not humor/rights claims.
    """
    batches=[]
    cat_category_titles=set()
    failures=[]
    searched=[]
    for kind,names in (("query",searches),("category",categories)):
        for phrase in names:
            try:
                results=(query_candidates(phrase,100) if kind=="query" else
                         category_candidates(phrase,100))
                batch=[]
                local_seen=set()
                for cand in results:
                    key=cand["title"].casefold()
                    if kind=="category":
                        cat_category_titles.add(key)
                    if key not in local_seen:
                        batch.append(cand)
                        local_seen.add(key)
                batches.append(batch)
                searched.append({"type":kind,"term":phrase,"found":len(batch)})
                print(f"[V17 {kind}] {phrase}: {len(batch)} candidates",flush=True)
            except Exception as err:
                failures.append({"type":kind,"term":phrase,"error":type(err).__name__})
                print(f"[V17 unavailable] {kind} {phrase}: {type(err).__name__}",flush=True)

    pooled={}
    offsets=[0]*len(batches)
    while len(pooled)<max_pool:
        read_any=False
        for index,batch in enumerate(batches):
            if offsets[index]>=len(batch):
                continue
            candidate=batch[offsets[index]]
            offsets[index]+=1
            read_any=True
            key=candidate["title"].casefold()
            if key not in pooled:
                entry=dict(candidate)
                entry["cat_category_evidence"]=key in cat_category_titles
                pooled[key]=entry
            elif key in cat_category_titles:
                pooled[key]["cat_category_evidence"]=True
            if len(pooled)>=max_pool:
                break
        if not read_any:
            break
    return list(pooled.values()), searched, failures

def editorial_excluded_titles(path="review/excluded_clips.json"):
    """Explicit evidence-based editorial exclusions, not rights claims."""
    f=Path(path)
    if not f.exists():
        return set()
    data=json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not isinstance(data.get("exclusions"),list):
        raise ValueError("Invalid editorial-exclusion ledger")
    return {str(row["title"]).casefold()
            for row in data["exclusions"]
            if isinstance(row,dict) and row.get("title")}


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

def make_review(out,limit=10,byte_budget=190*1024*1024,max_file=55*1024*1024,source_override=None):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    preview_dir=out/"V17_PREVIEWS"
    preview_dir.mkdir(exist_ok=True)
    frames_dir=out/"V17_FRAMES"
    frames_dir.mkdir(exist_ok=True)
    if source_override is None:
        candidates,queries,errors=collect_sources()
    else:
        if not isinstance(source_override,list) or len(source_override)>20:
            raise ValueError("Explicit curated candidates must be a list up to 20")
        candidates=[dict(item) for item in source_override]
        queries=[{"type":"curated_exact_file_titles","term":"creator-first source audit",
                  "found":len(candidates)}]
        errors=[]
    raw_count=len(candidates)
    irrelevant=[src for src in candidates if not likely_cat_candidate(src)]
    candidates=[src for src in candidates if likely_cat_candidate(src)]
    used=archived_titles()
    editorial_exclusions=editorial_excluded_titles()
    report={"status":"NEEDS_MANUAL_REVIEW","automated_humor_rating":None,
            "license_review_complete":False,"approved_for_publication":False,
            "queries":queries,"query_errors":errors,"raw_license_filtered_pool":raw_count,
            "cat_relevance_pool":len(candidates),
            "previously_used_title_count":len(used),
            "rejected":[{"title":x["title"],"reason":"REJECT_NOT_CAT_RELEVANT"}
                        for x in irrelevant],"candidates":[]}
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
        if name.casefold() in editorial_exclusions:
            report["rejected"].append({
                "title":name,"reason":"PRIOR_MOMENT_EDITORIAL_QA_REJECTED"})
            continue
        if is_external_reupload(src):
            report["rejected"].append({"title":name,"reason":"EXTERNAL_REUPLOAD_UNVERIFIED"})
            continue
        if int(src.get("size_bytes",0))>max_file:
            report["rejected"].append({"title":name,"reason":"DOWNLOAD_OVER_55MIB"})
            continue
        # Include up to three clips even for generic filenames.
        # A missing action word is not proof a video lacks a good moment.
        if group_used.get(group,0)>=3:
            report["rejected"].append({"title":name,"reason":"DUPLICATE_ACTION_CATEGORY"})
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
            elif not audition_seconds(duration):
                entry["status"]="REJECT_DURATION"
            else:
                preview_seconds=audition_seconds(duration)
                windows=window_candidates(local,duration,seconds=preview_seconds,count=2,max_scan=65)
                for ordinal,window in enumerate(windows,1):
                    start=float(window["start"])
                    if duration-start<preview_seconds:
                        continue
                    output=preview_dir/f"V17_{selected+1:02d}_M{ordinal}.mp4"
                    still=frames_dir/f"V17_{selected+1:02d}_M{ordinal}.jpg"
                    render_preview(local,start,output,seconds=preview_seconds)
                    moment_photo(local,min(start+preview_seconds/2,duration-0.15),still,width=320,height=210)
                    entry["moments"].append({
                        "start_sec":start,"preview_duration_sec":preview_seconds,
                        "movement_score_not_funny_score":window["motion"],
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
        f"위키미디어 CC BY/CC0 1차 메타데이터 통과 원본: **{raw_count}개**",
        f"고양이 관련 파일명·분류 근거 후보: **{len(candidates)}개** (실제 고양이 등장 여부는 재생 검수)",
        f"비고양이 관련성 차단: **{len(irrelevant)}개**",
        f"이전 실제 미리보기 탈락 원본 재수집 방지 목록: **{len(editorial_exclusions)}개**",
        "제외 목록은 저작권 결론이 아닌 이전 미리보기 장면의 편집 판단입니다.",
        "목표는 '재미있는 5개'를 검증하는 것이지 숫자 5를 무조건 채우는 게 아닙니다.",
        "‘움직임 점수’는 컷과 카메라 움직임에도 반응하므로 재미·웃음·반전을 뜻하지 않습니다.",
        "외부 YouTube·TikTok 재게시 파일은 저작자 권리가 미확인되어 우선 제외했습니다.",
        "최소 해상도 720×480 수준 이상, 원본 길이 4~240초, 원본 55MiB 이하.",
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
