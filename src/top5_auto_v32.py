#!/usr/bin/env python3
"""V32: auto topic -> 5 originals -> substitute stronger audited Pexels action
-> locked V28.3 TOP5 -> full MP4/rights gates. No publishing.

Pexels sources are one-by-one, manually curated; no API key, scraping or
license/YPP claim. The broader topical engine remains V30 for other topics.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,os
from pathlib import Path
from v12_sources import allowed_page
from top5 import fetch_json, extract_candidates, download_video
from v12_pexels_audition import download_single_pexels
from top5_auto_v30 import (choose_topic,select_sources,write_gates)
from top5_auto_v29 import (save_license_and_status,assemble_video,technical_qa,CUT_LENGTHS,get_frame)
from top5_hook_selection import HOOK_SECONDS, SourceShortage, choose_hook, identity
from v28_fullscreen_builder import SourceCrop

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


def apply_v37_story_and_door(topic,items,output):
    """V37: human-contact-sheet-selected door opening and original scene comedy.

    The user-locked template (including 60pt caption geometry) is not altered.
    This only adjusts rank 2 content and puts short setup-action-payoff writing
    in the same existing single-line reaction zone.
    """
    audit={"version":"V37","door_added":False,"original_story_captions":False,
           "publication_approved":False,"rights_independently_verified":False,
           "youtube_reused_content_approved":False,
           "license_sharealike_acknowledged":False}
    if topic["topic_id"]!="cat_surprises":
        return items,audit
    rows=[dict(row) for row in items]
    pair="Pexels PX-17536779"
    if any(row["title"]==pair for row in rows):
        try:
            from v37_cat_audition import commons_download
            src={"id":"commons-door","provider":"commons",
                 "title":"File:Cat opening door.webm",
                 "page_url":"https://commons.wikimedia.org/wiki/File:Cat_opening_door.webm",
                 "license_required":"by-sa/4.0"}
            p=Path(output)/"v37_cat_door.webm"
            license_data=commons_download(src,p)
            from top5 import probe_duration
            duration=float(probe_duration(p))
            if duration<22.05:
                raise ValueError("V37 exact 15.9-21.9 story window unavailable")
            row={"title":src["title"],
                 "source_page":src["page_url"],
                 "author":license_data["author"],
                 "license":license_data["license"],
                 "license_url":license_data["license_url"],
                 "source_claim":"Creator self-identifies on Commons; independent ownership check pending",
                 "local_path":str(p),"duration_sec":duration,
                 "cut_start":15.9,"motion_proxy":0,
                 "editorial_quality_heuristic":66.0,
                 "label":"앞발 문열기",
                 "caption":"진짜 문까지 열었다!",
                 "review_basis":"V37 source at 15.9-21.9 shows jump, handle and visibly opening door with >1s ending",
                 "rights_verified":False,"publication_approved":False,
                 "provenance_independently_verified":False,
                 "source_audio_approved":False,
                 "requires_sharealike_attribution":True}
            rows=[row if item["title"]==pair else item for item in rows]
            audit["door_added"]=True
            audit["license_sharealike_acknowledged"]=True
        except Exception as ex:
            audit["door_issue"]=type(ex).__name__
    scripts={
        # Issue #126 frame review: the rush is visible at 4.92s in the edit.
        "File:Cat Jumpscare.webm":[[0.1,"태평하게 누워 있더니"],[2.92,"카메라로 갑자기 돌진!"]],
        "Pexels PX-40826295":[[0.1,"길가에서 멈춰 서더니"],[2.1,"아예 바닥을 뒹군다ㅋㅋ"]],
        "Pexels PX-34689563":[[0.1,"소파 아래가 수상한데?"],[1.8,"분홍 공에 앞발 한 방!"]],
        "File:Cat opening door.webm":[[0.12,"손잡이에 도전 중!"],[2.35,"앞발로 밀고 기다리니"],[4.62,"진짜 열렸다!"]],
        "Pexels PX-17536779":[[0.1,"상자 안을 지키는 고양이"],[3.1,"밖에서 앞발 대결ㅋㅋ"]],
        # End the setup before the cat emerges into the gap around 22s.
        "File:Salto - Cat Jump.webm":[[0.12,"지붕 사이 거리 재는 중"],[0.92,"망설임 없이 도약!"]],
    }
    for row in rows:
        if row["title"]=="Pexels PX-40826295":
            row["clear_rank_rail"]=True
        script=scripts.get(row["title"])
        if script:
            row["caption_sequence"]=script
            row["original_commentary"]="V37 author-created two/three-act micro narration"
            audit["original_story_captions"]=True
    rows.sort(key=lambda r:(r["editorial_quality_heuristic"],r["title"]))
    if len(rows)!=5 or len({r["title"] for r in rows})!=5:
        raise RuntimeError("V37 count and diversity gate failed")
    return rows,audit

def v37_rights_and_description(items,output,audit):
    """Write attribution and editing evidence; no YouTube revenue approval."""
    notes=["# V37 publication-rights and source attribution draft","",
       "This is a review-only rough-cut. Only publish after independently confirming each item's actual author and third-party rights, and assessing substantial originality.",
       "No source audio is used; all audio was synthesized by our workflow.",""]
    for i,row in enumerate(items):
        notes.extend([f"## {5-i}위: {row['label']}",
            f"- Source: {row['source_page']}",
            f"- Credited author: {row['author']}",
            f"- Source licence: {row['license']}",
            f"- Licence URL: {row['license_url']}",
            "- Adaptation: 4-6s crop, aspect-preserving composition, original captions, synthesized audio and comparison ranking",
            "- Rights, third-party release, reused-content YPP: not independently cleared.",""])
    notes.extend([
       "## ShareAlike when the door opening scene is used",
       "For the CC BY-SA 4.0 original by Astropulse, identify the original source, author, terms and changed use in the YouTube description. Because it is adapted, any adapted contribution must be offered under compatible CC BY-SA terms. Review compliance before publication.",
       "- https://creativecommons.org/licenses/by-sa/4.0/",
       "- https://commons.wikimedia.org/wiki/File:Cat_opening_door.webm",
       "",
       "Publication: BLOCKED until applicable legal and YPP considerations have been reviewed; provider labels are not an independent audit."
    ])
    (Path(output)/"V37_ATTRIBUTION_AND_PUBLISH_GATES.md").write_text("\n".join(notes)+"\n",encoding="utf-8")
    (Path(output)/"V37_STORY_AND_RIGHTS_QA.json").write_text(
        json.dumps({"publish":False,"rights_independently_verified":False,
                    "reused_content_ypp_approved":False,
                    "door_added":audit["door_added"],
                    "source_count":len(items),
                    "act_timelines":[{"title":r["title"],"story":r.get("caption_sequence")}
                                     for r in items]},ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")

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
            row["replay_offset_sec"]=0.9
            row["hook_start"]=4.9
            row["timing_basis"]="V33 actual 0-10s source 18-frame QA and V33 full MP4 A/B"
            row["editorial_timing_reverified"]=True
        out.append(row)
    return out

def select_dog_audition_sources(topic,candidates,output):
    """Use actual downloaded Pexels audition assets, never merely count them.

    This is a review-only assembly. Title metadata is not proof of the action,
    funniness, authorship or YouTube reuse permission.
    """
    from top5 import probe_duration, motion_highlight
    audit_path=Path("output/dog_audition/DOG_AUDITION.json")
    if not audit_path.is_file():
        raise RuntimeError("DOG_AUDITION_MISSING: run V37 dog audition first")
    evidence=json.loads(audit_path.read_text(encoding="utf-8"))
    rows=[]
    failures=[]
    for src in evidence.get("candidates",[]):
        if src.get("status")!="AWAITING_EDITORIAL_FRAME_REVIEW":
            failures.append({"id":src.get("id"),"reason":src.get("status")})
            continue
        path=audit_path.parent/(src["id"]+".mp4")
        if not path.is_file():
            failures.append({"id":src["id"],"reason":"downloaded original missing"})
            continue
        try:
            duration=float(probe_duration(path))
            if duration<6.2:
                raise ValueError("source shorter than six-second rank")
            start,motion=motion_highlight(path,duration,seconds=5)
            start=max(0.0,min(float(start),duration-6.08))
            rows.append({
                "title":"Pexels dog "+src["id"],"provider":"pexels",
                "source_page":src["page_url"],"author":src["creator"],
                "license":"Pexels License","license_url":src["license_url"],
                "source_claim":"Provider listing only; authorship and rights not independently cleared",
                "local_path":str(path),"duration_sec":duration,
                "cut_start":round(start,2),"motion_proxy":float(motion),
                "editorial_quality_heuristic":min(45.0,25.0+float(motion)*0.2),
                "review_basis":"V37 source frame sheet generated; editorial action NOT yet verified",
                "label":src["title"],"caption":({"dog-fetch":"공을 향해 전력 질주!","dog-puppy":"앞발부터 나가는 순간","dog-snow":"눈밭 위 원반 추격","dog-field":"넓은 들판을 가로질러","dog-jump-person":"사람에게 달려드는 순간!","dog-fetch-ring":"원반을 향한 집중!","dog-bag-surprise":"가방에서 갑자기 등장!","dog-door-rush":"문 열리자 단체 출동!","dog-door-peek":"문 뒤에서 슬쩍 등장!"}.get(src["id"],"강아지의 움직임을 보세요")), 
                "rights_verified":False,"publication_approved":False,
                "comic_action_verified":False})
        except Exception as exc:
            failures.append({"id":src["id"],"reason":type(exc).__name__})
    # Commons sources are downloaded and metadata checked by the existing V30 gate.
    # Do not select medical, resting, hunting or unrelated videos to fill ranks.
    from top5_auto_v30 import select_sources
    commons=[]
    if candidates:
        try:
            commons,_=select_sources(candidates,output)
        except RuntimeError:
            # V30 requires five Commons items. Dog mode may have fewer.
            from top5 import download_video
            for i,src in enumerate(candidates[:12]):
                path=Path(output)/("dog_commons_%02d"%i+Path(src["title"]).suffix.lower())
                try:
                    download_video(src,path)
                    duration=float(probe_duration(path))
                    if duration<6.2 or duration>125: raise ValueError("duration")
                    start,motion=motion_highlight(path,duration,seconds=5)
                    if motion<0.1: raise ValueError("static")
                    commons.append({**src,"local_path":str(path),
                        "duration_sec":duration,
                        "cut_start":max(0.0,min(float(start),duration-6.08)),
                        "motion_proxy":float(motion),
                        "editorial_quality_heuristic":min(45.0,25.0+float(motion)*0.2),
                        "review_basis":"Commons metadata/motion only; action not verified",
                        "label":"강아지 행동 후보","caption":"무슨 일이 벌어질까?",
                        "rights_verified":False,"publication_approved":False,
                        "comic_action_verified":False})
                except Exception as exc:
                    path.unlink(missing_ok=True)
                    failures.append({"id":src.get("title"),"reason":type(exc).__name__})
    # Deterministic no-human fallback: exclude low-action footage when at least
    # five other real, downloaded originals remain. Never invent extra sources.
    # These are mechanical proxies, NOT a humor or rights approval.
    # Sampled run #49 frames showed bag and curled-up puppy footage as weak
    # action/payoff candidates. Prefer other downloaded action families first;
    # retain these only as explicitly logged technical fallbacks.
    # #126 contact-sheet QA: the Commons puppies-playing source shows a nearly
    # motionless dog lying on a bed in the selected rank-2 interval (16-20s).
    # The field source shows a distant tiny dog in a wide shot (2-4s).
    # These are source-specific editorial warnings, NOT copyright findings.
    weak={"Pexels dog dog-field","Pexels dog dog-snow",
          "Pexels dog dog-bag-surprise","Pexels dog dog-puppy",
          "File:Puppiesplaying-tokyoarea-jan7-2020.webm"}
    strong=[r for r in rows+commons if r.get("title") not in weak]
    fallback=[r for r in rows+commons if r.get("title") in weak]
    # Prefer distinct action families; do not mistake metadata for verified humor.
    # The older strategy repeatedly selected fetch/catch footage.
    def action_family(item):
        title=str(item.get("title","")).lower()
        if "bag-surprise" in title:
            return "bag_surprise"
        if "door-rush" in title:
            return "door_rush"
        if "door-peek" in title:
            return "door_peek"
        if "jump-person" in title:
            return "jump_person"
        if "pupp" in title:
            return "puppies"
        if "snow" in title:
            return "snow"
        if "field" in title:
            return "field"
        if any(k in title for k in ("fetch","catch","frisbee","ring")):
            return "fetch"
        return "other:"+title
    # Prefer new action families for audition, never treat titles as verified comedy.
    fresh={"dog-door-rush","dog-door-peek","dog-jump-person"}
    strong.sort(key=lambda r:(0 if any(x in r.get("title","") for x in fresh) else 1,r.get("title","")))
    # Known visually weak sources are NOT allowed back into a new render.
    # If fewer than five distinct strong candidates exist, stop and source more.
    # This is a quality gate, not a claim that remaining footage is humorous.
    pool=list(strong)
    # Deterministic alternative selection for bounded automated re-edits.
    # Variant 0 is default. Variants 1-3 rotate downloaded strong sources.
    variant=max(0,min(3,int(os.environ.get("TOP5_REPAIR_VARIANT","0"))))
    if variant and len(strong)>5:
        shift=variant%len(strong)
        pool=strong[shift:]+strong[:shift]
    combined=[]
    seen=set()
    for item in pool:
        family=action_family(item)
        if family not in seen:
            combined.append(item)
            seen.add(family)
    for item in pool:
        if item not in combined:
            combined.append(item)
    (Path(output)/"AUTO_SOURCE_REPLACEMENT.json").write_text(json.dumps({
        "strategy":"prefer distinct action families, then fill only from real downloaded originals",
        "repair_variant":variant,
        "action_families_selected":[action_family(r) for r in combined[:5]],
        "weak_candidates":[r["title"] for r in fallback],
        "strong_candidates":[r["title"] for r in strong],
        "fallback_used":[r["title"] for r in combined[:5] if r in fallback],
        "fallback_editorial_warning":(
            "Run #126 contact-sheet QA: wide field dog is tiny; Commons puppies clip "
            "shows low-action resting dog. Replace with independently reviewed "
            "visible setup/action/payoff footage; fallback is never humor-cleared."),
        "semantic_humor_certified":False,"publication_approved":False
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (Path(output)/"DOG_SOURCE_BRIDGE.json").write_text(json.dumps({
        "pexels_technically_eligible":len(rows),"commons_technically_eligible":len(commons),
        "total":len(combined),"failures":failures,
        "editorial_action_verified":False,"rights_verified":False,
        "publication_approved":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if len(combined)<5:
        raise RuntimeError("DOG_SOURCE_SHORTAGE: %d/5 real eligible originals; "
                           "Pexels audition now connected, no filler allowed"%len(combined))
    # The first selected item becomes rank 5 and the LAST becomes rank 1.
    # Previous source-priority ordering inadvertently promoted the weakest
    # fallback (dog-field: empty grass in run #123) to the top rank and hook.
    # Put known weak, unreviewed fallback clips in low ranks; this is a
    # mechanical risk reduction, not a verified humor score or rights audit.
    selected=combined[:5]
    selected.sort(key=lambda row:(
        0 if row in fallback else 1,
        float(row.get("editorial_quality_heuristic",0)),
        float(row.get("motion_proxy",0)),
        str(row.get("title",""))))
    (Path(output)/"DOG_RANK_ORDER_AUDIT.json").write_text(json.dumps({
        "rank_5_to_1":[{"rank":5-i,"title":row["title"],
                        "weak_fallback":row in fallback,
                        "motion_proxy":row.get("motion_proxy")}
                       for i,row in enumerate(selected)],
        "ranking_verified_for_humor":False,
        "rights_verified":False,"publication_approved":False,
        "reason":"run #123 rank1 dog-field empty frame; never place known weak fallback at rank1 when stronger source exists"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return selected,failures,combined

def source_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# Issue #126: the white cat lunges after a brief pause and both cats tumble.
# Bind the reviewed opening to the
# original bytes so a replacement upload cannot inherit the edit.
REVIEWED_HOOK_STARTS = {
    "78103e4630f8c096f1836dd83b1a0e04e5dbb46f781e8692e2eee5823275c1cf": 95.875,
}

REVIEWED_EDITS = {
    "a26b3af399817a63048b51b8f3da8e420b29ee3592e2836fc1a5b5f14143a627": {
        "cut_start":2.875,
        "caption_sequence":None,
        "caption":"태평하게 누워 있더니…",
        "source_crop":SourceCrop(width=1160,height=1080,y=0,start_x=360,end_x=620,
                                 pan_start=7.0,pan_end=7.8),
        "clear_rank_rail":True,
        "mobile_caption_y":1430,
    },
    "a3c3a070ed28764ae2306b123e2e6c5a36cc680ae4a596f94dc0a54e89571bc8": {
        "playback_rate":2/3,
        "caption_sequence":[[0.12,"지붕 사이로 도약 · ⅔속도"]],
        "caption":"지붕 사이로 도약 · ⅔속도",
        "source_crop":SourceCrop(width=420,height=560,y=100,start_x=0,end_x=300,
                                 pan_start=4.15,pan_end=6.65),
        "clear_rank_rail":True,
        "mobile_caption_y":1590,
    },
    "e5824e2c9ba6cb04cc84e4a624509c1fd43941617b34fd88e69751f199208f81": {
        "source_crop":SourceCrop(width=2040,height=3060,y=300,start_x=120,end_x=0,
                                 pan_start=12.35,pan_end=13.1),
        "clear_rank_rail":True,
        "mobile_caption_y":1660,
    },
    "a7fec4a995d907f7e2d18a5010887034d323059474599046ab91d19f13f41968": {
        "source_crop":SourceCrop(width=970,height=1460,y=280,start_x=0,end_x=0,
                                 pan_start=0,pan_end=1),
        "clear_rank_rail":True,
        "mobile_caption_y":1659,
    },
}


def select_v32_hook(ranked, pool, ranked_hashes, output):
    """Screen unused originals first and retain a byte-bound audit for either mode."""
    attempts = []
    audit = {"status": "NO_DISTINCT_HOOK", "independent_hook": False,
             "editorial_action_verified": False, "rights_verified": False,
             "publication_approved": False, "attempts": attempts}
    ranked_ids = {identity(row) for row in ranked}
    ranked_titles = {row["title"] for row in ranked}
    digests = {identity(row): digest for row, digest in zip(ranked, ranked_hashes, strict=True)}
    used_hashes = set(ranked_hashes)
    durations = [sec*row.get("playback_rate",1.0)
                 for row,sec in zip(ranked,CUT_LENGTHS.values(),strict=True)]
    candidates = []
    for row in sorted(pool, key=lambda item: -float(item.get("motion_proxy", 0))):
        if identity(row) in ranked_ids or row["title"] in ranked_titles:
            continue
        path = Path(row["local_path"])
        if not path.is_file() or not path.stat().st_size:
            attempts.append({"title": row["title"], "reason_code": "HOOK_SOURCE_MISSING"})
            continue
        digest = source_digest(path)
        if digest in used_hashes or identity(row) in digests:
            attempts.append({"title": row["title"], "reason_code": "HOOK_SOURCE_DUPLICATE"})
            continue
        digests[identity(row)] = digest
        used_hashes.add(digest)
        if digest in REVIEWED_HOOK_STARTS:
            candidates.insert(0, {**row, "hook_start": REVIEWED_HOOK_STARTS[digest]})
        else:
            candidates.append(row)
    path = output / "INDEPENDENT_HOOK_AUDIT.json"
    try:
        hook = choose_hook(ranked, [*candidates, *ranked], durations, attempts)
    except SourceShortage as exc:
        audit["reason_code"] = exc.code
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        raise
    index = next((i for i, row in enumerate(ranked) if identity(row) == identity(hook)), None)
    audit.update(status="HOOK_SELECTED", independent_hook=index is None,
                 hook_mode=hook["hook_mode"], sha256=digests[identity(hook)],
                 title=hook["title"], source_page=hook.get("source_page"),
                 source_start_sec=hook["hook_start"], source_end_sec=round(hook["hook_start"]+HOOK_SECONDS, 3),
                 reused_rank=None if index is None else 5-index,
                 ranked_cut_sec=None if index is None else
                 [ranked[index]["cut_start"], round(ranked[index]["cut_start"]+durations[index], 3)])
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return hook, audit, path


def write_rendered_hook_evidence(video, audit, path):
    # Capture the opening of the delivered MP4, including its actual overlays.
    from PIL import Image
    timestamps = (0.25, 1.0, 1.75)
    sheet = Image.new("RGB", (216 * len(timestamps), 384))
    for i, timestamp in enumerate(timestamps):
        sheet.paste(get_frame(video, timestamp).resize((216, 384)), (i*216, 0))
    contact_sheet = path.with_name("V32_RENDERED_HOOK_QA.jpg")
    sheet.save(contact_sheet, quality=90)
    audit.update(status="HOOK_RENDER_VERIFIED", rendered_video_sha256=source_digest(video),
                 rendered_hook_range_sec=[0, HOOK_SECONDS], rendered_sample_times_sec=timestamps,
                 rendered_sample_sheet=contact_sheet.name)
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


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
    hook_pool=[]
    if topic["topic_id"]=="dog_surprises":
        selected,attempts,hook_pool=select_dog_audition_sources(topic,candidates,output)
    else:
        if len(candidates)<5: raise RuntimeError("insufficient rights-metadata sources")
        selected,attempts=select_sources(candidates,output,reserve_pool=hook_pool)
    final,audit=add_challenger(topic,selected,output)
    final,sofa_audit=add_sofa_challenger(topic,final,output)
    (output/"V35_SOFA_CHALLENGER_QA.json").write_text(json.dumps(
        sofa_audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    final,v36_audit=add_v36_action_clips(topic,final,output)
    (output/"V36_CANDIDATE_REPLACEMENTS_QA.json").write_text(
        json.dumps(v36_audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    final=apply_rank_one_story_timing(final)
    final,v37_audit=apply_v37_story_and_door(topic,final,output)
    # Apply bounded, auditable feedback to the actual render inputs.
    # The file is optional; invalid feedback never authorizes publication.
    from top5_feedback_repair import load_and_apply
    final,feedback_report=load_and_apply(
        final,"review/feedback/dog_latest.json",output/"FEEDBACK_REPAIR_APPLIED.json")
    (output/"V32_CHALLENGER_SELECTION.json").write_text(json.dumps(
        audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_gates(output,topic,final,attempts,recommendations)
    # Persist a deterministic, non-publishing replacement manifest for later QA.
    # These are provisional candidates, not verified clip reviews.
    replacement_manifest={
        "schema_version":1,"topic":topic["topic_id"],
        "clips":[{"rank":5-i,"source_page":item.get("source_page"),
                  "title":item.get("title"),"verified":False,
                  "editorial_score":None,"rights_independently_cleared":False}
                 for i,item in enumerate(final)],
        "repair_attempt":0,
        "next_step":"Independent clip-level review and source-rights evidence required",
        "publication_approved":False
    }
    (output/"TOP5_REPLACEMENT_REVIEW_INPUT.json").write_text(
        json.dumps(replacement_manifest,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")
    # Audit selected input bytes; this is not a copyright clearance.
    selected_evidence=[]
    mobile_captions=topic["topic_id"]=="cat_surprises"
    for i,item in enumerate(final):
        original=Path(item["local_path"])
        if not original.is_file() or original.stat().st_size==0:
            raise RuntimeError("SELECTED_SOURCE_MISSING: "+str(original))
        digest=source_digest(original)
        if mobile_captions:
            item.update(REVIEWED_EDITS.get(digest,{}))
        rate=item.get("playback_rate",1.0)
        selected_evidence.append({
            "rank":5-i,"source_page":item.get("source_page"),
            "source_path":str(original),"sha256":digest,
            "source_start_sec":item["cut_start"],
            "source_end_sec":round(item["cut_start"]+list(CUT_LENGTHS.values())[i]*rate,3),
            "playback_rate":rate,
            "size_bytes":original.stat().st_size,
            "rights_verified":False,"publication_approved":False})
    if len(selected_evidence)!=5 or len({r["sha256"] for r in selected_evidence})!=5:
        raise RuntimeError("SELECTED_SOURCE_DUPLICATE_OR_MISSING")
    v37_rights_and_description(final,output,v37_audit)
    (output/"SELECTED_SOURCE_PROVENANCE.json").write_text(json.dumps({
        "selected":selected_evidence,"rights_verified":False,
        "editorial_score_verified":False,"publication_approved":False
    },ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    hook_source,hook_audit,hook_path=select_v32_hook(
        final,[*hook_pool,*selected],[row["sha256"] for row in selected_evidence],output)
    save_license_and_status(topic,final,recommendations,attempts,output,hook_source)
    reviewed_hook=REVIEWED_HOOK_STARTS.get(hook_audit["sha256"])==hook_source["hook_start"]
    hook_caption="가만있다가 갑자기 돌진!" if reviewed_hook else "다음 행동을 맞혀 보세요"
    video=assemble_video(topic,final,output,hook_source,
                         moving_ending=True,hook_caption=hook_caption,
                         hook_caption_y=(1455 if reviewed_hook else 1712) if mobile_captions else 1190,
                         mobile_captions=mobile_captions)
    qa=technical_qa(video,output,topic,final)
    write_rendered_hook_evidence(video,hook_audit,hook_path)
    qa["hook_mode"]=hook_audit["hook_mode"]
    qa["version"]="V37"
    qa["curated_new_video_used"]=bool(audit["download_ok"]) if topic["topic_id"]!="dog_surprises" else len([item for item in final if item.get("provider")=="pexels"])>0
    qa["dog_pexels_originals_in_edit"]=sum(item.get("provider")=="pexels" for item in final) if topic["topic_id"]=="dog_surprises" else None
    qa["dog_editorial_action_verified"]=False if topic["topic_id"]=="dog_surprises" else None
    qa["source_permissions_fully_cleared"]=False
    qa["publication_approved"]=False
    qa["v36_actions_added"]=int(v36_audit["jumpscare_added"])+int(v36_audit["pair_added"])
    qa["v37_actual_door_selected"]=bool(v37_audit["door_added"])
    qa["v37_original_micro_story_written"]=bool(v37_audit["original_story_captions"])
    qa["original_style_preserved"]="V28.3 title and rank rail with mobile captions" if mobile_captions else "V28.3 locked, caption 60pt"
    qa["rendered_design"]=qa["original_style_preserved"]
    qa["audio_listening"]="UNVERIFIED"
    (output/"V32_TECHNICAL_QA.json").write_text(json.dumps(qa,
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V32 VIDEO COMPLETE",video,"new source =",qa["curated_new_video_used"],
          "publication = NO",flush=True)

if __name__=="__main__":main()
