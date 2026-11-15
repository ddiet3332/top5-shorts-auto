#!/usr/bin/env python3
"""V36 preliminary cat-action audition: frame contact sheets, not video approval.

Sources must originate on an official individual asset page. This script
does NOT promote sources, infer humor from motion, or approve publication.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"src"))
from top5 import fetch_json, download_video, extract_candidates
from v12_sources import allowed_page
from v12_pexels_audition import download_single_pexels

OUTPUT=Path("output/v36_audition")
SOURCES=[
    {"id":"commons-jumpscare","provider":"commons","title":"File:Cat Jumpscare.webm",
     "page_url":"https://commons.wikimedia.org/wiki/File:Cat_Jumpscare.webm",
     "source_claim":"Uploader says own work; licensing on Commons page marked CC0 1.0"},
    {"id":"pexels-box","provider":"pexels","title":"Cat jumping into box",
     "page_url":"https://www.pexels.com/video/a-cat-jumping-in-the-box-5495527/",
     "creator":"Meow Meow","license_label":"Pexels License",
     "license_url":"https://www.pexels.com/license/"},
    {"id":"pexels-two-cats","provider":"pexels","title":"Playful kitten interacts with cat in cardboard box",
     "page_url":"https://www.pexels.com/video/cat-fight-17536779/",
     "creator":"aslı aydoğdu","license_label":"Pexels License",
     "license_url":"https://www.pexels.com/license/"},
]
def cmd(args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=150)

def get_info(p):
    data=json.loads(cmd(["ffprobe","-v","error","-show_streams",
        "-show_format","-of","json",str(p)]))
    v=next(s for s in data["streams"] if s["codec_type"]=="video")
    return {"duration_sec":float(data["format"]["duration"]),
            "width":v["width"],"height":v["height"],
            "codec":v["codec_name"],"filesize":p.stat().st_size}

def original_commons(src,target):
    response=fetch_json({"action":"query","format":"json","formatversion":"2",
        "titles":src["title"],"prop":"imageinfo",
        "iiprop":"url|size|mime|extmetadata"})
    matches=list(extract_candidates(response))
    assert len(matches)==1, "License is not CC BY or CC0; or video is too large"
    item=matches[0]
    assert item["title"]==src["title"]
    assert item["license"].upper().find("CC0")>=0, "Audition source expected CC0"
    download_video(item,target)
    return {"license":item["license"],"author":item["author"],
            "license_url":item["license_url"],"actual_source_url":item["source_page"]}

def original_pexels(src,target):
    assert allowed_page(src), "Pexels page must pass allowlist"
    info=download_single_pexels(src,target,max_bytes=125*1024*1024)
    return {"license":"Pexels License (provider label only)",
            "license_url":src["license_url"],"author":src["creator"],
            "pexels_info":info}

def sheets(video,slug,out,duration):
    folder=out/f"{slug}-frames"
    folder.mkdir(parents=True,exist_ok=True)
    cmd(["ffmpeg","-hide_banner","-v","error","-y","-i",str(video),
         "-vf","fps=2,scale=240:-2","-q:v","5",str(folder/"%04d.jpg")])
    frames=sorted(folder.glob("*.jpg"))
    out_files=[]
    for page,start in enumerate(range(0,len(frames),20)):
        subset=frames[start:start+20]
        tile=Image.new("RGB",(5*252,4*265),(18,20,25))
        d=ImageDraw.Draw(tile)
        for i,p in enumerate(subset):
            im=Image.open(p).convert("RGB")
            im.thumbnail((240,226))
            x=i%5*252+6
            y=i//5*265+5
            tile.paste(im,(x,y))
            d.text((x,y+229),f"{(start+i)*0.5:.1f}s",fill=(240,240,240))
        name=f"{slug}_timeline_{page:02d}_{start/2:.0f}-{(start+len(subset))/2:.0f}s.jpg"
        tile.save(out/name,quality=86)
        out_files.append(name)
    return out_files

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    result=[]
    for src in SOURCES:
        row={k:v for k,v in src.items() if k!="source_claim"}
        row.update({"rights_independently_verified":False,
                    "youtube_reused_content_approved":False,
                    "creative_action_verified":False,
                    "publish_approved":False,"selected":False})
        target=OUTPUT/(src["id"]+".mp4" if src["provider"]=="pexels" else src["id"]+".webm")
        try:
            row.update(original_commons(src,target) if src["provider"]=="commons"
                       else original_pexels(src,target))
            row.update(get_info(target))
            if row["duration_sec"]<6.0 or row["height"]<360:
                row["status"]="REJECTED_MEDIA_TECH"
            else:
                row["status"]="READY_FOR_HUMAN_FRAME_REVIEW"
                row["frame_sheets"]=sheets(target,src["id"],OUTPUT,row["duration_sec"])
        except Exception as exc:
            row["status"]="FAILED_OR_REJECTED"
            row["error_type"]=type(exc).__name__
            row["error_detail"]=str(exc)[:200]
        result.append(row)
        print(src["id"],row["status"],flush=True)
    (OUTPUT/"V36_AUDITION.json").write_text(json.dumps({
        "audition_only":True,"publication_approved":False,
        "source_promotions":0,"candidates":result},ensure_ascii=False,indent=2)+"\n")
    if not any(r["status"]=="READY_FOR_HUMAN_FRAME_REVIEW" for r in result):
        raise RuntimeError("None of the three source videos could be auditioned")

if __name__=="__main__":
    main()
