#!/usr/bin/env python3
"""V30 review-only source quality gates + adaptive discovery.

No paid API, no AI claim of semantic understanding, and NO automatic publication.
The video template remains V28.3 with only the user-approved caption 60pt.
"""
from __future__ import annotations
import argparse
import json
import re
import math
from pathlib import Path
from collections import Counter

from top5 import query_candidates, category_candidates, download_video, probe_duration, motion_highlight
from top5_auto_v29 import (
    find_seed_candidates, title_score, story_label,
    assemble_video, technical_qa, save_license_and_status, CUT_LENGTHS
)
from top5_hook_selection import SourceShortage, choose_hook, identity

BASE=Path(__file__).resolve().parents[1]
CHECKED=BASE/"review/v29_checked_actions.json"
BLOCK=re.compile(r"youtube|tiktok|instagram|facebook|vimeo|flickr",re.I)
PROMOTED={
    "File:Moomin1.webm":("면봉 놀이","이 작은 장난감에 진심!"),
    "File:Larry the cat and Chloé playing (100111224612).webm":
        ("함께 놀기","누가 더 신났을까?"),
}
MIN_STRONG=50
MAX_DOWNLOADS=15

def checked_scenes():
    # Prior real-frame editorial evidence can guide later automatic reranks.
    # It never proves rights or quality of a different crop/window.
    memory={}
    for path in (CHECKED, BASE/"review/v30_checked_actions.json"):
        if path.exists():
            memory.update(json.loads(path.read_text(encoding="utf-8")).get("reviewed",{}))
    return memory

def discover_for_topic(topic,discover=True):
    rows={}
    failures=[]
    try:
        for x in find_seed_candidates(topic):
            rows[x["title"]]=x
    except Exception as e:
        failures.append("seed API: "+type(e).__name__)
    if discover:
        for phrase in topic.get("search",[])[:12]:
            try:
                for x in query_candidates(phrase,per_query=45):
                    rows.setdefault(x["title"],x)
            except Exception as e:
                failures.append("search "+phrase+": "+type(e).__name__)
    if discover:
        for category in topic.get("commons_categories",[])[:5]:
            try:
                for x in category_candidates(category,per_query=100):
                    rows.setdefault(x["title"],x)
            except Exception as e:
                failures.append("category "+category+": "+type(e).__name__)
    reviewed=checked_scenes()
    scored=[]
    seeds=set(topic.get("seeds",[]))
    for row in rows.values():
        name=row["title"]
        normalized_name=name.casefold()
        if any(term.casefold() in normalized_name for term in topic.get("exclude_title_contains",[])):
            continue
        meta_score=title_score(row,topic)
        if topic.get("require_action_in_title",False) and not any(action.casefold() in normalized_name for action in topic["actions"]):
            if name not in seeds:
                continue
        if name in seeds and meta_score<0 and not BLOCK.search(row.get("source_claim","")):
            meta_score=4.0  # explicitly curated neutral-name files, metadata only
        if meta_score<=0:
            continue
        evidence=reviewed.get(name)
        if evidence and evidence.get("story_strength",0)<MIN_STRONG:
            # Known weak / misleading shots cannot outrank unseen candidates again.
            continue
        score=meta_score+(10 if name in seeds else 0)+(evidence.get("story_strength",0)*0.35 if evidence else 0)
        scored.append({**row,"title_score":round(meta_score,2),
                       "discovery_rank":round(score,2)})
    scored.sort(key=lambda x:(-x["discovery_rank"],x["title"]))
    return scored,failures

def choose_topic(topics,requested):
    standings=[]
    by_topic={}
    for topic in topics:
        available,errors=discover_for_topic(topic,discover=True)
        by_topic[topic["topic_id"]]=available
        standings.append({
            "topic_id":topic["topic_id"],
            "headline":topic["headline"],
            "metadata_eligible":len(available),
            "heuristic_score":round(sum(x["discovery_rank"] for x in available[:5]),2),
            "errors":errors,
            "confirmed_funny_clips":0,
            "method":"metadata and previous manually reviewed frames, not semantic AI",
        })
    standings.sort(key=lambda x:(-min(x["metadata_eligible"],5),
                                 -x["heuristic_score"],x["topic_id"]))
    topic_id=(requested if requested!="auto" else next(
        (r["topic_id"] for r in standings if r["metadata_eligible"]>=5),
        standings[0]["topic_id"]))
    found=next((t for t in topics if t["topic_id"]==topic_id),None)
    if found is None:
        raise ValueError("Unknown topic")
    return found,by_topic[topic_id],standings

def apply_curated_cut_shift(title,start,duration):
    """Bounded adjustment from 40-frame human QA; never changes rights approval."""
    location=BASE/"review/v31_cut_adjustments.json"
    if not location.exists():
        return round(float(start),2)
    memory=json.loads(location.read_text(encoding="utf-8")).get("offsets",{})
    if title not in memory:
        return round(float(start),2)
    shift=float(memory[title]["start_shift_seconds"])
    if not math.isfinite(shift) or abs(shift)>2.5:
        raise ValueError("Unreasonable editorial cut adjustment")
    return round(max(0.0,min(float(start)+shift,float(duration)-6.08)),2)

def select_sources(candidates,out,*,with_hook=False):
    library=Path(out)/"originals"
    library.mkdir(parents=True,exist_ok=True)
    evidence=checked_scenes()
    accepted=[]
    attempts=[]
    seen=set()
    for idx,src in enumerate(candidates[:MAX_DOWNLOADS],1):
        suffix=Path(src["title"]).suffix.lower()
        if suffix not in (".webm",".mp4",".ogv"):
            attempts.append({"title":src["title"],"status":"REJECTED","reason_code":"UNSUPPORTED_CONTAINER"})
            continue
        if identity(src) in seen:
            attempts.append({"title":src["title"],"status":"REJECTED","reason_code":"DUPLICATE_SOURCE"})
            continue
        seen.add(identity(src))
        target=library/f"clip_{idx:02}{suffix}"
        row={"title":src["title"],"source_page":src["source_page"],
             "status":"unchecked"}
        try:
            download_video(src,target)
            dur=probe_duration(target)
            if not 6.2<=dur<=125:
                raise ValueError("video duration incompatible with TOP5 6-sec cut")
            at,motion=motion_highlight(target,dur,seconds=5)
            at=max(0.0,min(float(at),dur-6.08))
            at=apply_curated_cut_shift(src["title"],at,dur)
            if motion<0.1:
                raise ValueError("near-static motion")
            reviewed=evidence.get(src["title"])
            if reviewed:
                quality=float(reviewed["story_strength"])
                label=reviewed["label"]
                reaction=reviewed["reaction"]
                status="prior_mp4_frames_reviewed"
            else:
                # Not a semantic funny score; only prioritizes candidate review.
                quality=min(58.0,30.0+min(20.0,motion*.32)+min(8.,src["title_score"]))
                label,reaction=PROMOTED.get(
                    src["title"],(story_label(src["title"]),"이 장면을 놓치지 마세요!"))
                status="metadata_and_motion_only_UNVERIFIED"
            accepted.append({**src,"local_path":str(target),
                "cut_start":round(at,2),"duration_sec":round(dur,2),
                "motion_proxy":round(float(motion),3),
                "editorial_quality_heuristic":quality,
                "review_basis":status,"label":label,"caption":reaction,
                "rights_verified":False,"publication_approved":False,
                "comic_action_verified":False})
            row.update({"status":"PROVISIONAL","duration":round(dur,2),
                        "motion_proxy":round(float(motion),3),
                        "review_status":status})
        except Exception as ex:
            target.unlink(missing_ok=True)
            row.update({"status":"REJECTED","why":type(ex).__name__+
                         ": "+str(ex)[:110]})
        attempts.append(row)
        print("CANDIDATE",idx,row["title"],row["status"],flush=True)
        if len(accepted)>=9:
            break
    if len(accepted)<5:
        out=Path(out)
        (out/"V30_CANDIDATES.json").write_text(
            json.dumps(attempts,ensure_ascii=False,indent=2),encoding="utf-8")
        raise SourceShortage("SOURCE_SHORTAGE",f"기술 검사를 통과한 원본 {len(accepted)}/5",attempts)
    accepted.sort(key=lambda x:-x["editorial_quality_heuristic"])
    used=[]
    author_count=Counter()
    label_count=Counter()
    for row in accepted:
        if author_count[row["author"]]>=2 or label_count[row["label"]]>=2:
            continue
        used.append(row)
        author_count[row["author"]]+=1
        label_count[row["label"]]+=1
        if len(used)==5:
            break
    if len(used)<5:
        for row in accepted:
            if row not in used:
                used.append(row)
            if len(used)==5:
                break
    used.sort(key=lambda x:(x["editorial_quality_heuristic"],x["title"]))
    if with_hook:
        hook=choose_hook(used,accepted,list(CUT_LENGTHS.values()),attempts)
        return used,attempts,hook
    return used,attempts

def write_gates(output,topic,items,attempts,standings):
    output=Path(output)
    ranks=[]
    for i,video in enumerate(items):
        ranks.append({
            "rank":5-i,"title":video["title"],"caption":video["caption"],
            "quality_prior_or_proxy":video["editorial_quality_heuristic"],
            "evidence":video["review_basis"],
            "scene_action_verified_for_this_cut":False,
            "real_action_semantics_certified":False,
            "source_rights_independently_cleared":False,
        })
    n_prior=sum(r["evidence"]=="prior_mp4_frames_reviewed" for r in ranks)
    report={
        "topic":topic["topic_id"],
        "auto_topic_selected":True,
        "scene_rank_heuristic_only":True,
        "previously_reviewed_sources":n_prior,
        "new_unverified_sources":5-n_prior,
        "quality_target_75_met":None,
        "scores_not_computed_without_full_editorial_review":True,
        "publication_approved":False,
        "copyright_and_ypp_verified":False,
        "fail_closed_if_rights_incomplete":True,
        "rank_5_to_1":ranks,
        "attempts":attempts,"topic_standings":standings,
    }
    (output/"V30_CREATIVE_AND_RIGHTS_GATES.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--topics",default="sample/top5_auto_topics_v30.json")
    ap.add_argument("--topic",default="auto")
    ap.add_argument("--output",default="output/v30_auto")
    args=ap.parse_args()
    out=Path(args.output)
    out.mkdir(exist_ok=True,parents=True)
    topics=json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic,candidates,standings=choose_topic(topics,args.topic)
    print("TOPIC",topic["topic_id"],"CANDIDATES",len(candidates),flush=True)
    (out/"V30_TOPICS.json").write_text(json.dumps(standings,ensure_ascii=False,
                          indent=2)+"\n",encoding="utf-8")
    try:
        items,attempts,hook_source=select_sources(candidates,out,with_hook=True)
    except SourceShortage as exc:
        (out/"SOURCE_ATTEMPTS.json").write_text(json.dumps(
            [{"topic_id":topic["topic_id"],"reason_code":exc.code,"candidates":exc.attempts}],
            ensure_ascii=False,indent=2),encoding="utf-8")
        raise
    write_gates(out,topic,items,attempts,standings)
    save_license_and_status(topic,items,standings,attempts,out,hook_source)
    video=assemble_video(topic,items,out,hook_source)
    qa=technical_qa(video,out,topic,items)
    print("V30 SUCCESS",video,"decode=",qa["full_decode"],"PUBLISH=NO",flush=True)

if __name__=="__main__":
    main()
