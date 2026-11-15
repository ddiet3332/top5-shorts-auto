#!/usr/bin/env python3
"""V32: auto topic -> 5 originals -> substitute stronger audited Pexels action
-> locked V28.3 TOP5 -> full MP4/rights gates. No publishing.

Pexels sources are one-by-one, manually curated; no API key, scraping or
license/YPP claim. The broader topical engine remains V30 for other topics.
"""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
from v12_sources import allowed_page
from v12_pexels_audition import download_single_pexels
from top5_auto_v30 import (choose_topic,select_sources,write_gates)
from top5_auto_v29 import (save_license_and_status,assemble_video,technical_qa)

CHALLENGER={
 "id":"PX-40826295",
 "provider":"pexels",
 "title":"Playful Cat Rolling on Urban Sidewalk",
 "page_url":"https://www.pexels.com/video/playful-cat-rolling-on-urban-sidewalk-40826295/",
 "creator":"Zeynep Coşkun",
 "license_label":"Pexels License",
 "license_url":"https://www.pexels.com/license/",
}
# 0-6s motion was inspected from actual preview contact sheet before promotion.
AUDITED_START=0.0
AUDITED_ACTION="cat rolling on city sidewalk"
AUDITED_REACTION="길바닥이 그렇게 좋니?ㅋㅋ"

def challenger_row(source,path,info):
    if not allowed_page(source): raise ValueError("Official individual Pexels source required")
    if not 6.1<float(info["duration_sec"])<121:
        raise ValueError("Clip cannot cover 5s rank")
    return {
      "title":"Pexels "+source["id"],"provider":"pexels",
      "source_page":source["page_url"],
      "author":source["creator"],
      "license":"Pexels License",
      "license_url":source["license_url"],
      "source_claim":"Pexels content license page; original authorship not independently verified",
      "local_path":str(path),"duration_sec":float(info["duration_sec"]),
      "cut_start":AUDITED_START,"motion_proxy":0.0,
      "editorial_quality_heuristic":59.0,
      "review_basis":"V32 actual 0-6s source contact-sheet human review",
      "label":"발라당 구르기","caption":AUDITED_REACTION,
      "actual_0_to_6s_action_reviewed":True,
      "provenance_independently_verified":False,
      "rights_verified":False,"publication_approved":False,
      "comic_action_verified":False,"source_audio_approved":False
    }

def add_challenger(topic,items,output):
    """Swap only when source is different, downloads legally, and beats #5."""
    audit={"attempted":False,"download_ok":False,
           "source_licensing_provenance_verified":False,
           "reused_content_approved":False,"publication_approved":False}
    if topic["topic_id"]!="cat_surprises":
        audit["reason"]="No manually auditioned stronger source for this subject"
        return items,audit
    audit["attempted"]=True
    if not allowed_page(CHALLENGER):
        audit["reason"]="Curated source URL/label did not pass allowlist"
        return items,audit
    temp=Path(output)/"curated_pexels_cat_roll.mp4"
    try:
        info=download_single_pexels(CHALLENGER,temp,max_bytes=125*1024*1024)
        challenger=challenger_row(CHALLENGER,temp,info)
        worst=items[0]
        if challenger["editorial_quality_heuristic"]<=worst["editorial_quality_heuristic"]:
            temp.unlink(missing_ok=True)
            audit["reason"]="New source insufficiently strong to displace previous 5th"
            return items,audit
        # This ranking uses a human-inspected six-second sample, NOT
        # future-facing general AI understanding of video humor.
        selected=items[1:]+[challenger]
        selected.sort(key=lambda row:(row["editorial_quality_heuristic"],row["title"]))
        audit.update({"download_ok":True,"replaced":worst["title"],
           "added":CHALLENGER["page_url"],"original_author_metadata":CHALLENGER["creator"],
           "video_duration_seconds":info["duration_sec"],
           "source_0_to_6s_action_reviewed":True,
           "selected_rank":5-next(i for i,x in enumerate(selected)
                                   if x["title"]==challenger["title"]),
           "license_status":"PEXELS_PROVIDER_TERMS_ONLY",
           "rights_and_ypp_status":"REQUIRES_INDEPENDENT_REVIEW"})
        return selected,audit
    except Exception as e:
        temp.unlink(missing_ok=True)
        audit.update({"reason":"Pexels source unavailable; use prior Commons-only draft",
           "failure_type":type(e).__name__})
        return items,audit

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--topics",default="sample/top5_auto_topics_v30.json")
    ap.add_argument("--topic",default="auto")
    ap.add_argument("--output",default="output/v32_auto")
    args=ap.parse_args()
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    topics=json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic,candidates,recommendations=choose_topic(topics,args.topic)
    (output/"TOPIC_RECOMMENDATIONS_V32.json").write_text(
        json.dumps({"chosen_topic":topic["topic_id"],"topics":recommendations,
        "method":"metadata availability and previous editorial judgments",
        "measured_trends_or_views":False},ensure_ascii=False,indent=2)+"\n")
    if len(candidates)<5: raise RuntimeError("insufficient rights-metadata sources")
    selected,attempts=select_sources(candidates,output)
    final,audit=add_challenger(topic,selected,output)
    (output/"V32_CHALLENGER_SELECTION.json").write_text(json.dumps(
        audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_gates(output,topic,final,attempts,recommendations)
    save_license_and_status(topic,final,recommendations,attempts,output)
    video=assemble_video(topic,final,output)
    qa=technical_qa(video,output,topic,final)
    qa["version"]="V32"
    qa["curated_new_video_used"]=bool(audit["download_ok"])
    qa["source_permissions_fully_cleared"]=False
    qa["publication_approved"]=False
    qa["original_style_preserved"]="V28.3 locked, caption 60pt"
    (output/"V32_TECHNICAL_QA.json").write_text(json.dumps(qa,
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V32 VIDEO COMPLETE",video,"new source =",audit["download_ok"],
          "publication = NO",flush=True)

if __name__=="__main__":main()
