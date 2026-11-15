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
from top5 import fetch_json, extract_candidates, download_video
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

SOFA_CHALLENGER={
    "id":"PX-34689563","provider":"pexels",
    "title":"Playful Cat Under Sofa with Toy Ball",
    "page_url":"https://www.pexels.com/video/playful-cat-under-sofa-with-toy-ball-34689563/",
    "creator":"nilay ortanca",
    "license_label":"Pexels License",
    "license_url":"https://www.pexels.com/license/",
}

def add_sofa_challenger(topic,items,output):
    """Original six-second candidate visually inspected in V34 contacts.

    For this format the selected rank3 is only four seconds:
    9.29-13.29 original shows hidden kitten -> reaches for pink toy.
    Rights remain unverified; no Pexels footage used as original audio.
    """
    audit={"attempted":False,"selected":False,"publication_approved":False,
           "source_rights_independently_verified":False}
    if topic["topic_id"]!="cat_surprises" or not any(
        row["title"]=="File:Moomin1.webm" for row in items):
        audit["reason"]="No compatible original-to-replace"
        return items,audit
    audit["attempted"]=True
    temp=Path(output)/"curated_pexels_sofa.mp4"
    try:
        if not allowed_page(SOFA_CHALLENGER):
            raise ValueError("Unapproved original license page")
        info=download_single_pexels(SOFA_CHALLENGER,temp,
                                    max_bytes=125*1024*1024)
        row=challenger_row(SOFA_CHALLENGER,temp,info)
        if float(info["duration_sec"])<13.5:
            raise ValueError("Audited action 9.29-13.29 not present")
        row.update({"cut_start":9.29,"editorial_quality_heuristic":63.0,
                    "label":"소파 속 매복",
                    "caption":"숨어 있다가 장난감 급습!ㅋㅋ",
                    "review_basis":"V34 actual 9.29-13.29 original source 24-frame QA",
                    "storytelling_setup_action_payoff_in_rank3":True})
        chosen=[x for x in items if x["title"]!="File:Moomin1.webm"]+[row]
        chosen.sort(key=lambda x:(x["editorial_quality_heuristic"],x["title"]))
        audit.update({"selected":True,"replaced":"File:Moomin1.webm",
           "added":SOFA_CHALLENGER["page_url"],"rank3_start":9.29,
           "original_author_metadata":SOFA_CHALLENGER["creator"],
           "Pexels_terms_not_YouTube_monetization":True})
        return chosen,audit
    except Exception as ex:
        temp.unlink(missing_ok=True)
        audit.update({"failure_type":type(ex).__name__,
             "reason":"Candidate rejected; retain original 3rd"})
        return items,audit


# V36 manually inspected source windows. Editorial evidence is limited to
# real source contact sheets; no source-rights or YouTube approval is implied.
V36_JUMPSCARE_TITLE="File:Cat Jumpscare.webm"
V36_PAIR_SOURCE={
    "id":"PX-17536779", "provider":"pexels",
    "title":"Playful Kitten Interacts with Cat in Cardboard Box",
    "page_url":"https://www.pexels.com/video/cat-fight-17536779/",
    "creator":"aslı aydoğdu", "license_label":"Pexels License",
    "license_url":"https://www.pexels.com/license/"
}

def add_v36_action_clips(topic,items,output):
    """Try a real CC0 rush and an original vertical paw-play interaction.

    Exact names and source windows are fixed from original 0.5s contact sheets.
    Never claim the action is funny, legally cleared, or revenue-safe solely
    because these frame sheets show motion.
    """
    audit={"version":"V36","publication_approved":False,
           "rights_independently_verified":False,
           "youtube_reused_content_approved":False,
           "jumpscare_added":False,"pair_added":False,
           "attempts":[]}
    if topic["topic_id"]!="cat_surprises":
        audit["reason"]="New clips were not auditioned for this topic"
        return items,audit
    rows=[dict(t) for t in items]
    if any(r["title"]=="File:Cat in a Bag.webm" for r in rows):
        path=Path(output)/"v36_cat_jumpscare.webm"
        try:
            data=fetch_json({
                "action":"query","format":"json","formatversion":"2",
                "titles":V36_JUMPSCARE_TITLE,
                "prop":"imageinfo","iiprop":"url|size|mime|extmetadata"})
            matches=[c for c in extract_candidates(data)
                     if c["title"]==V36_JUMPSCARE_TITLE]
            if len(matches)!=1 or matches[0]["license"]!="CC0":
                raise ValueError("CC0 provider metadata missing or ambiguous")
            original=matches[0]
            download_video(original,path)
            from top5 import probe_duration
            duration=float(probe_duration(path))
            if duration<8.2:
                raise ValueError("Audited rush event 4.0-8.0 unavailable")
            replacement={
                "title":V36_JUMPSCARE_TITLE,
                "source_page":original["source_page"],
                "author":original["author"],
                "license":original["license"],
                "license_url":original["license_url"],
                "source_claim":original["source_claim"],
                "local_path":str(path),"duration_sec":duration,
                "cut_start":4.0, "motion_proxy":0,
                "editorial_quality_heuristic":58.0,
                "review_basis":"V36 original 0-10s 0.5s source frames; 4-8s action",
                "label":"기습 카메라 돌진",
                "caption":"굴러가다 갑자기 돌진!ㅋㅋ",
                "rights_verified":False,"publication_approved":False,
                "provenance_independently_verified":False,
                "source_audio_approved":False}
            rows=[replacement if z["title"]=="File:Cat in a Bag.webm" else z
                  for z in rows]
            audit["jumpscare_added"]=True
            audit["attempts"].append({
                "replaced":"File:Cat in a Bag.webm","added":V36_JUMPSCARE_TITLE,
                "start":4.0,"duration":4.0,"candidate_evidence":"V36 contact sheet",
                "license_metadata":"CC0; independent ownership not proven"})
        except Exception as ex:
            path.unlink(missing_ok=True)
            audit["attempts"].append({
                "added":V36_JUMPSCARE_TITLE,"failed_type":type(ex).__name__,
                "selected":False})
    if any(r["title"]=="File:Katzensprung in Zeitlupe.webm" for r in rows):
        path=Path(output)/"v36_pexels_two_cats.mp4"
        try:
            if not allowed_page(V36_PAIR_SOURCE):
                raise ValueError("Pexels individual source validation failed")
            info=download_single_pexels(V36_PAIR_SOURCE,path,
                                         max_bytes=125*1024*1024)
            if float(info["duration_sec"])<38.0:
                raise ValueError("Audited interaction 31.4-37.4 absent")
            replacement=challenger_row(V36_PAIR_SOURCE,path,info)
            replacement.update({
                "cut_start":31.4,"editorial_quality_heuristic":64.0,
                "label":"상자 앞발 대결",
                "caption":"상자 수비수, 앞발로 딱!ㅋㅋ",
                "review_basis":"V36 original 30-40s 0.5s source frames; 31.4-37.4s",
                "actual_rank2_interval_contact_sheet_reviewed":True})
            rows=[replacement if z["title"]=="File:Katzensprung in Zeitlupe.webm"
                  else z for z in rows]
            audit["pair_added"]=True
            audit["attempts"].append({
                "replaced":"File:Katzensprung in Zeitlupe.webm",
                "added":V36_PAIR_SOURCE["page_url"],
                "start":31.4,"duration":6.0,
                "candidate_evidence":"V36 source 30-40s contact sheet",
                "license_metadata":"Pexels License only; rights and YPP not proven"})
        except Exception as ex:
            path.unlink(missing_ok=True)
            audit["attempts"].append({
                "added":V36_PAIR_SOURCE["page_url"],
                "failed_type":type(ex).__name__,"selected":False})
    rows.sort(key=lambda r:(r["editorial_quality_heuristic"],r["title"]))
    if len(rows)!=5 or len({r["title"] for r in rows})!=5:
        raise RuntimeError("V36 five distinct sources required")
    return rows,audit

def apply_rank_one_story_timing(items):
    """Based on V33 visual review of original Salto 0-10s.

    Source 2.03-8.03 sec contains pre-jump set-up + full jump with <0.3s
    of empty tail. The 0-2sec hook stays mid-air, separate from rank 1.
    This affects SOURCE TIMING, not the user-approved design geometry.
    """
    out=[]
    for item in items:
        row=dict(item)
        # Creative captions add a distinct observation to each rank without
        # changing the user's approved 60pt font, position or geometry.
        original_reactions={
            "File:Cat in a Bag.webm":"쇼핑백에 이사 왔나?ㅋㅋ",
            "Pexels PX-40826295":"바닥이 전용 마사지기ㅋㅋ",
            "File:Moomin1.webm":"면봉 하나에 앞발 발사ㅋㅋ",
            "File:Katzensprung in Zeitlupe.webm":"도약에서 착지까지 쭉!",
            "File:Salto - Cat Jump.webm":"지붕 사이를 정말 넘는다!"
        }
        if row["title"] in original_reactions:
            row["caption"]=original_reactions[row["title"]]
        if row["title"]=="File:Salto - Cat Jump.webm" and float(row["duration_sec"])>=8.8:
            # Original source frame scan: the cat first enters around 3.0s
            # and exits near 8.1s. 2.65–8.65 balances both tails.
            row["cut_start"]=2.65
            row["hook_start"]=4.9
            row["timing_basis"]="V33 actual 0-10s source 18-frame QA and V33 full MP4 A/B"
            row["editorial_timing_reverified"]=True
        out.append(row)
    return out

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
    final,sofa_audit=add_sofa_challenger(topic,final,output)
    (output/"V35_SOFA_CHALLENGER_QA.json").write_text(json.dumps(
        sofa_audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    final,v36_audit=add_v36_action_clips(topic,final,output)
    (output/"V36_CANDIDATE_REPLACEMENTS_QA.json").write_text(
        json.dumps(v36_audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    final=apply_rank_one_story_timing(final)
    (output/"V32_CHALLENGER_SELECTION.json").write_text(json.dumps(
        audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_gates(output,topic,final,attempts,recommendations)
    save_license_and_status(topic,final,recommendations,attempts,output)
    video=assemble_video(topic,final,output)
    qa=technical_qa(video,output,topic,final)
    qa["version"]="V36"
    qa["curated_new_video_used"]=bool(audit["download_ok"])
    qa["source_permissions_fully_cleared"]=False
    qa["publication_approved"]=False
    qa["v36_actions_added"]=int(v36_audit["jumpscare_added"])+int(v36_audit["pair_added"])
    qa["original_style_preserved"]="V28.3 locked, caption 60pt"
    (output/"V32_TECHNICAL_QA.json").write_text(json.dumps(qa,
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V32 VIDEO COMPLETE",video,"new source =",audit["download_ok"],
          "publication = NO",flush=True)

if __name__=="__main__":main()
