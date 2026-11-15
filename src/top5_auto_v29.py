#!/usr/bin/env python3
"""TOP5 V29: choose a grounded topic, select CC0/CC BY candidates and render
a review-only 30-second MP4 using the user's LOCKED V28.3/60pt design.

This does not use a paid AI API. Metadata ranking + frame motion are *proxies*,
not vision understanding, rights ownership proof, or YouTube YPP clearance.
Never publish automatically. Never silently replace real footage with AI.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from top5 import (fetch_json, extract_candidates, query_candidates, download_video,
                  probe_duration, motion_highlight)
from v28_fullscreen_builder import (ASS_HEAD, SEGMENTS, W, H, FPS, run,
                                    cue, create_scene, get_frame)
from v25_audio_remaster import create_soundtrack

# The fixed design must match V28.3, including the user's 60pt caption change.
assert "Style: Caption,NanumSquare,60," in ASS_HEAD
CUT_LENGTHS = {"rank5": 4, "rank4": 5, "rank3": 4, "rank2": 6, "rank1": 6}
REACTIONS = {
    "hook": "당신이라면 몇 위?",
    "rank5": "잠깐, 다시 보세요!",
    "rank4": "다음 움직임 주목!",
    "rank3": "딱 이 순간입니다!",
    "rank2": "끝까지 놓치지 마요!",
    "rank1": "당신의 1위는?",
}
WORD_LABELS = [
    (("jumpscare","surpris","startled"),"깜짝 반응"),
    (("chasing","chase","pigeon"),"추격전"),
    (("jump","salto","spring","hopping"),"도약"),
    (("playing","play","toy","moomin"),"장난감 놀이"),
    (("roll","bounce","spin"),"회전"),
    (("fall","slip","fail","tumble"),"뜻밖의 실수"),
    (("storm","lightning","strike"),"순간 포착"),
]
BLOCK_EXTERNAL = re.compile(r"(?:youtube|tiktok|instagram|facebook|vimeo|flickr)",re.I)

def story_label(title: str) -> str:
    title=title.lower()
    for needles, label in WORD_LABELS:
        if any(term in title for term in needles):
            return label
    return "예상 밖 순간"

def title_score(row, topic) -> float:
    name=row["title"].lower()
    matches=sum(1 for kw in topic["relevance"] if kw in name)
    acts=sum(1 for kw in topic["actions"] if kw in name)
    license=row.get("license","").lower()
    source_claim=row.get("source_claim","")
    if not matches or BLOCK_EXTERNAL.search(source_claim):
        return -999
    if row.get("size_bytes",0)>36*1024*1024:
        return -999
    if not row.get("author"):
        return -999
    if not row.get("license_url","").startswith(("https://creativecommons.org/","http://creativecommons.org/")):
        return -999
    score=matches*2.0 + min(acts,2)*2.5 + (3 if "cc0" in license else 1)
    score+=max(0,2.0-row.get("size_bytes",0)/(30*1024*1024))
    return score

def find_seed_candidates(topic):
    titles=topic.get("seeds",[])
    if not titles:
        return []
    data=fetch_json({"action":"query","format":"json","formatversion":"2",
            "titles":"|".join(titles),"prop":"imageinfo",
            "iiprop":"url|size|mime|extmetadata"})
    return list(extract_candidates(data))

def find_for_topic(topic, do_search=True):
    found={}
    errors=[]
    try:
        for row in find_seed_candidates(topic):
            found[row["title"]]=row
    except Exception as e:
        errors.append("seed lookup: "+type(e).__name__)
    if do_search:
        for phrase in topic["search"][:2]:
            try:
                for row in query_candidates(phrase,per_query=35):
                    found.setdefault(row["title"],row)
            except Exception as e:
                errors.append(phrase+": "+type(e).__name__)
    scored=[]
    for row in found.values():
        score=title_score(row,topic)
        if score>0:
            scored.append({**row,"title_score":round(score,2)})
    scored.sort(key=lambda r:(-r["title_score"],r["title"]))
    return scored,errors

def recommend_topics(topics, forced=None):
    recommendations=[]
    catalog={}
    for topic in topics:
        # Each category is evaluated using available video metadata. No fake
        # claims about trends, views, actual humor, or original authorship.
        candidates,errors=find_for_topic(topic,do_search=True)
        catalog[topic["topic_id"]]=candidates
        recommendations.append({
            "topic_id":topic["topic_id"],"headline":topic["headline"],
            "category":topic["category"],
            "eligible_metadata_count":len(candidates),
            "discovery_heuristic":round(sum(x["title_score"] for x in candidates[:5]),2),
            "error_notes":errors,"actual_funny_action_verified":False,
            "license_state":"metadata_only",
        })
    recommendations.sort(key=lambda x:(-min(5,x["eligible_metadata_count"]),
                     -x["discovery_heuristic"],x["topic_id"]))
    chosen_id=forced if forced and forced!="auto" else next(
        (x["topic_id"] for x in recommendations if x["eligible_metadata_count"]>=5),None)
    if not chosen_id:
        raise RuntimeError("No topic has at least 5 metadata-eligible originals")
    if forced not in (None,"auto") and chosen_id not in catalog:
        raise ValueError("Unrecognized topic ID")
    return next(t for t in topics if t["topic_id"]==chosen_id),catalog[chosen_id],recommendations

def select_sources(candidates,output,limit=11):
    sources=output/"source_assets"
    sources.mkdir(parents=True,exist_ok=True)
    eligible=[]
    attempts=[]
    for number, cand in enumerate(candidates[:limit],1):
        title=cand["title"]
        suff=Path(title).suffix.lower()
        if suff not in (".webm",".ogv",".ogg",".mp4"):
            continue
        target=sources/f"original_{number:02}{suff}"
        failure=None
        try:
            download_video(cand,target)
            dur=probe_duration(target)
            if not 6.15 <=dur<=120:
                raise ValueError("Length incompatible with six-second ranking cut")
            cut, motion=motion_highlight(target,dur,seconds=5)
            # Motion score is NOT a measure of comedic quality.
            start=max(0,min(float(cut),dur-6.05))
            if motion < 0.1:
                raise ValueError("Near-static source in motion screening")
            eligible.append({**cand,
                "local_path":str(target),"duration_sec":round(dur,2),
                "cut_start":round(start,2),"motion_proxy":round(float(motion),3),
                "label":story_label(title),
                "rights_verified":False,"publication_approved":False,
                "comic_action_verified":False})
        except Exception as e:
            failure=type(e).__name__+": "+str(e)[:110]
            target.unlink(missing_ok=True)
        attempts.append({"title":title,"downloaded":failure is None,
                         "failure":failure,"actual_action_verified":False})
        print("SOURCE",number,title,"PASS" if not failure else failure,flush=True)
        if len(eligible)>=6:
            break
    if len(eligible)<5:
        raise RuntimeError(f"Only {len(eligible)} eligible playable sources, need 5")
    # Distinctness constraint: not more than two identical label categories.
    used=[]
    label_counts={}
    for row in sorted(eligible,key=lambda x:(x["motion_proxy"]+x["title_score"]*0.15),reverse=True):
        if label_counts.get(row["label"],0)>=2:
            continue
        used.append(row)
        label_counts[row["label"]]=label_counts.get(row["label"],0)+1
        if len(used)==5:
            break
    if len(used)<5:
        used=eligible[:5]
    # Ordered from 5th to 1st by technical/editing heuristic, not an
    # objective ranking of how funny real-world events are.
    used.sort(key=lambda x:(x["motion_proxy"]+x["title_score"]*.15,x["title"]))
    return used,attempts

def build_dynamic_subtitles(path,topic,items):
    subtitle_lines=[]
    subtitle_lines.append(cue(0,27,"MainTopic",topic["headline"],540,140,8))
    subtitle_lines.append(cue(0,27,"TopFive","TOP5",540,214,8))
    rank_titles={5-i:clip["label"] for i,clip in enumerate(items)}
    positions={"hook":1,"rank5":5,"rank4":4,"rank3":3,"rank2":2,"rank1":1}
    start=0
    for label,sec in SEGMENTS:
        end=start+sec
        if label!="outro":
            active=positions[label]
            for rank in range(1,6):
                y=485+(rank-1)*143
                style="Active" if rank==active else "Rank"
                subtitle_lines.append(cue(start,end,style,f"{rank}위",35,y))
                if rank==active:
                    subtitle_lines.append(cue(start,end,"RankName",
                              rank_titles[rank],35,y+61))
            reaction=REACTIONS[label]
            time=start + (0.0 if label=="hook" else
                 min(1.1,sec*.22))
            # Original V28.3 x/y, color, font, and align remain unchanged.
            subtitle_lines.append(cue(time,end,"Caption",reaction,504,1190,5))
        start=end
    path.write_text(ASS_HEAD+"\n".join(subtitle_lines)+"\n",encoding="utf-8")
    return subtitle_lines

def render_dynamic_endcard(items,path):
    image=Image.new("RGB",(W,H),"#070C11")
    draw=ImageDraw.Draw(image)
    font_path=subprocess.check_output(["fc-match","-f","%{file}","NanumSquare"],
                                      text=True).strip()
    ft=lambda n:ImageFont.truetype(font_path,n)
    draw.rounded_rectangle((42,150,1038,435),radius=36,fill="#13202B")
    draw.text((80,192),"5개의 순간",font=ft(70),fill="#F5D04E")
    draw.text((80,300),"당신의 1위는?",font=ft(46),fill="white")
    places=[(50,455,521,980),(559,455,1030,980),
            (50,1010,360,1485),(385,1010,695,1485),(720,1010,1030,1485)]
    for index,rect in enumerate(places):
        rank=index+1
        item=items[5-rank]
        x0,y0,x1,y1=rect
        moment=min(item["duration_sec"]-.15,item["cut_start"]+2)
        frame=get_frame(item["local_path"],moment)
        thumb=ImageOps.fit(frame,(x1-x0-14,y1-y0-100),Image.Resampling.LANCZOS)
        draw.rounded_rectangle(rect,radius=21,fill="#233442",
                               outline="#465A68",width=2)
        image.paste(thumb,(x0+7,y0+7))
        draw.text((x0+18,y1-73),f"{rank}위",
                  font=ft(39 if rank<=2 else 31),fill="#F5D04E")
        draw.text((x0+94 if rank<=2 else x0+86,y1-69),
                  item["label"][:8],
                  font=ft(27 if rank<=2 else 21),fill="white")
    draw.text((80,1680),"실제 원본에서 선정한 5개 장면",
              font=ft(30),fill="#D5E1EA")
    image.save(path,quality=93)

def save_license_and_status(topic,items,recommendations,attempts,output):
    credits=[f"# {topic['video_subject']} — 사용 출처 및 상태",
            "", "본 영상은 비공개 검수용 초안이며 게시 승인된 영상이 아닙니다.",
            "모든 소스 오디오는 제거하고 자체 합성 사운드만 사용했습니다.",""]
    evidence=[]
    for i,row in enumerate(items):
        rank=5-i
        credits.extend([
            f"## {rank}위 — {row['title']}",
            f"- 원본: {row['source_page']}",
            f"- 작성자(메타데이터): {row['author']}",
            f"- 표시 라이선스: {row['license']} ({row['license_url']})",
            "- 변경 사항: 일부 구간 발췌, 화면 배치, 색 보조 배경, 순위·자막·효과음 삽입",
            "- 원저작권자/초상권/음악/상표/수익화 검증: 미완료", ""
        ])
        evidence.append({k:row.get(k) for k in
            ("title","source_page","author","license","license_url",
             "cut_start","duration_sec","motion_proxy","label")})
    (output/"SOURCE_CREDITS_REVIEW.md").write_text("\n".join(credits),encoding="utf-8")
    (output/"TOPIC_RECOMMENDATIONS.json").write_text(json.dumps(
        {"chosen_topic":topic["topic_id"],"rankings":recommendations,
         "selection_method":"metadata and motion proxies, not paid AI vision",
         "license_and_YPP_verified":False},ensure_ascii=False,indent=2),
        encoding="utf-8")
    (output/"SOURCE_SELECTION_REVIEW.json").write_text(json.dumps(
        {"items_in_rank_5_to_1_order":evidence,"attempted":attempts,
         "creative_action_human_verified":False,"publication_approved":False},
         ensure_ascii=False,indent=2),encoding="utf-8")

def assemble_video(topic,items,output):
    work=output/"work"
    work.mkdir(parents=True,exist_ok=True)
    segment_files=[]
    first=items[-1]
    hook=work/"part_00.mp4"
    hook_at=min(first["duration_sec"]-2.1,first["cut_start"]+1.3)
    create_scene(first["local_path"],max(0,hook_at),2,hook)
    segment_files.append(hook)
    for number,(name,sec) in enumerate(SEGMENTS[1:-1],1):
        clip=items[number-1]
        part=work/f"part_{number:02}.mp4"
        start=clip["cut_start"]
        if start+sec>clip["duration_sec"]+.03:
            raise ValueError("Source action ends before selected rank cut")
        create_scene(clip["local_path"],start,sec,part)
        segment_files.append(part)
    card=work/"original_5_clip_endcard.jpg"
    render_dynamic_endcard(items,card)
    ending=work/"part_06.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-loop","1",
         "-framerate","24","-i",str(card),"-t","3","-vf","format=yuv420p",
         "-c:v","libx264","-preset","veryfast","-crf","23",
         "-r","24","-an",str(ending)],timeout=50)
    segment_files.append(ending)
    listing=work/"files.txt"
    listing.write_text("".join("file '"+str(x.resolve()).replace("'","'\\''")+
                  "'\n" for x in segment_files),encoding="utf-8")
    combined=work/"combined.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-f","concat",
         "-safe","0","-i",str(listing),"-c","copy",str(combined)],timeout=90)
    subtitles=work/"captions.ass"
    build_dynamic_subtitles(subtitles,topic,items)
    audio=work/"synth_music.wav"
    create_soundtrack(audio)
    final=output/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-i",str(combined),
         "-i",str(audio),"-vf",f"ass={subtitles}",
         "-map","0:v:0","-map","1:a:0",
         "-c:v","libx264","-preset","veryfast","-crf","22","-r","24",
         "-c:a","aac","-b:a","160k","-ar","48000",
         "-af","loudnorm=I=-21:TP=-2.2:LRA=7",
         "-t","30","-movflags","+faststart",str(final)],timeout=420)
    return final

def technical_qa(video,output,topic,items):
    info=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-of","json",
         "-show_streams","-show_format",str(video)],text=True))
    vv=[s for s in info["streams"] if s["codec_type"]=="video"]
    aa=[s for s in info["streams"] if s["codec_type"]=="audio"]
    if (len(vv)!=1 or len(aa)!=1 or vv[0]["codec_name"]!="h264"
        or aa[0]["codec_name"]!="aac"
        or (vv[0]["width"],vv[0]["height"])!=(W,H)
        or vv[0]["r_frame_rate"]!="24/1"
        or not 29.94<float(info["format"]["duration"])<30.12):
        raise RuntimeError("Full 30 second H264/AAC format gate failed")
    run(["ffmpeg","-hide_banner","-v","error","-xerror",
         "-i",str(video),"-map","0:v:0","-map","0:a:0",
         "-f","null","-"],timeout=360)
    ts=[.8,2.8,5.2,7.4,9.4,12.8,14,17.8,20,23.8,25.4,28.1]
    sheet=Image.new("RGB",(216*6,384*2),"black")
    for i,t in enumerate(ts):
        frame=get_frame(video,t).resize((216,384))
        sheet.paste(frame,((i%6)*216,(i//6)*384))
    sheet.save(output/"V29_ACTUAL_12FRAME_QA.jpg",quality=90)
    qa={"video":video.name,"topic":topic["topic_id"],
        "duration_seconds":float(info["format"]["duration"]),
        "resolution":"1080x1920","fps":24,
        "video_codec":"h264","audio_codec":"aac","full_decode":"PASS",
        "source_count":len(items),"topic_selection_automated":True,
        "source_selection_automated":True,"render_automated":True,
        "technical_qa_automated":True,"rendered_design":"V28.3 locked + caption 60",
        "creative_score_100":None,"funny_action_verified":False,
        "source_provenance_independently_verified":False,
        "third_party_rights_cleared":False,
        "youtube_reused_content_cleared":False,
        "publication_approved":False,"status":"REVIEW_ONLY"}
    (output/"V29_TECHNICAL_QA.json").write_text(
        json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return qa

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--topics",default="sample/top5_auto_topics.json")
    parser.add_argument("--topic",default="auto")
    parser.add_argument("--output",default="output/v29_auto")
    args=parser.parse_args()
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    topics=json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic,candidates,recommended=recommend_topics(topics,args.topic)
    print("TOPIC RECOMMENDED",topic["topic_id"],"candidate count",len(candidates),flush=True)
    items,attempts=select_sources(candidates,output)
    save_license_and_status(topic,items,recommended,attempts,output)
    video=assemble_video(topic,items,output)
    qa=technical_qa(video,output,topic,items)
    print("SUCCESS REVIEW ONLY",video,qa["full_decode"],flush=True)

if __name__=="__main__":
    main()
