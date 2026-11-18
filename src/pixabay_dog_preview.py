#!/usr/bin/env python3
"""Produce a real, clearly marked dog-footage REVIEW MP4 from Pixabay API results.
Never claims copyright clearance, humor scoring or publication approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
from pixabay_dog_inventory import collect

DOG=re.compile(r"(?<![a-z])(dog|dogs|puppy|puppies|canine|pup)(?![a-z])",re.I)
REJECT=re.compile(r"(?<![a-z])(cartoon|animation|animated|3d|cgi|render|illustration|wolf|wolves|fox|robot|ai-generated|ai generated)(?![a-z])",re.I)
def run(cmd):
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=210)

def download(url,path,max_bytes=60*1024*1024):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not (parsed.hostname=="cdn.pixabay.com" or parsed.hostname=="pixabay.com" or parsed.hostname.endswith(".pixabay.com")):
        raise ValueError("Untrusted Pixabay delivery host")
    req=urllib.request.Request(url,headers={"User-Agent":"TOP5DogReview/1.0"})
    tmp=path.with_suffix(".part")
    try:
        with urllib.request.urlopen(req,timeout=50) as resp, tmp.open("wb") as out:
            actual=urllib.parse.urlsplit(resp.geturl())
            if actual.scheme!="https" or not (actual.hostname=="cdn.pixabay.com" or actual.hostname=="pixabay.com" or actual.hostname.endswith(".pixabay.com")):
                raise ValueError("Untrusted video redirect")
            size=0
            for chunk in iter(lambda:resp.read(1024*1024),b""):
                size+=len(chunk)
                if size>max_bytes: raise ValueError("Video too large")
                out.write(chunk)
        if size<8192: raise ValueError("Invalid video")
        tmp.replace(path)
        return size
    finally:
        tmp.unlink(missing_ok=True)

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
       "-of","default=noprint_wrappers=1:nokey=1",str(path)],
       capture_output=True,text=True,timeout=25,check=True)
    return float(p.stdout.strip())

def build(key,output,query="funny puppy"):
    if not key: raise ValueError("PIXABAY_API_KEY missing")
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    params=urllib.parse.urlencode({"key":key,"q":query,"per_page":80,"safesearch":"true","order":"popular"})
    request=urllib.request.Request("https://pixabay.com/api/videos/?"+params,
                                  headers={"User-Agent":"TOP5DogReview/1.0","Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=40) as response:
        data=json.load(response)
    candidates=data.get("hits",[])
    rows=[];parts=[]
    for hit in candidates:
        if len(parts)>=5: break
        if not DOG.search(hit.get("tags","")): continue
        if REJECT.search(hit.get("tags","")): continue
        if float(hit.get("duration") or 0)<5.3: continue
        video=hit.get("videos") or {}
        variant=next((video.get(k) for k in ("medium","small","large") if (video.get(k) or {}).get("url")),None)
        if not variant: continue
        ident=hit.get("id")
        if not isinstance(ident,int): continue
        source=out/f"source_{ident}.mp4"
        clip=out/f"part_{len(parts)+1}.mp4"
        try:
            download(variant["url"],source)
            if probe(source)<5.2: raise ValueError("Insufficient duration")
            vf=("scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,setsar=1,fps=24,format=yuv420p,"
                "drawbox=x=0:y=0:w=iw:h=115:color=black@0.75:t=fill,"
                "drawtext=text='SOURCE REVIEW - NOT PUBLISHABLE':"
                "x=(w-text_w)/2:y=45:fontsize=34:fontcolor=white")
            run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(source),
                 "-t","5","-vf",vf,"-an","-c:v","libx264","-preset","veryfast",
                 "-crf","26","-pix_fmt","yuv420p",str(clip)])
            if probe(clip)<4.9: raise ValueError("Short render")
            parts.append(clip)
            rows.append({"provider":"pixabay","id":ident,"page_url":hit.get("pageURL"),
                         "creator":hit.get("user"),"tags":hit.get("tags"),
                         "source_duration":hit.get("duration"),
                         "actual_video_downloaded":True,"decoded_preview":True,
                         "editorial_score":None,"rights_verified":False,
                         "likeness_verified":False,"publication_approved":False})
        except Exception as e:
            print("Rejected Pixabay candidate",ident,type(e).__name__,flush=True)
            clip.unlink(missing_ok=True)
        finally:
            source.unlink(missing_ok=True)
    report={"query":query,"api_candidates":len(candidates),"usable_previews":len(parts),
            "status":"REVIEW_ONLY" if len(parts)==5 else "BLOCKED_INSUFFICIENT_REAL_MEDIA",
            "publication_approved":False,"candidates":rows}
    if len(parts)==5:
        listing=out/"concat.txt"
        listing.write_text("".join("file '"+p.name+"'\n" for p in parts),encoding="utf-8")
        final=out/"DOG_TOP5_SOURCE_REVIEW_ONLY_25s.mp4"
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
             "-i",str(listing),"-f","lavfi","-i","anullsrc=r=48000:cl=stereo",
             "-t","25","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
             "-b:a","96k","-movflags","+faststart",str(final)])
        report["video_filename"]=final.name
        report["video_sha256"]=hashlib.sha256(final.read_bytes()).hexdigest()
        report["video_duration_sec"]=round(probe(final),3)
        report["status"]="RENDERED_NOT_EDITORIALLY_APPROVED"
    (out/"DOG_PIXABAY_RENDER_AUDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for p in parts:p.unlink(missing_ok=True)
    print("Real previews:",len(parts),"; rendered:",bool(report.get("video_filename")),
          "; publication approved: FALSE",flush=True)
    if len(parts)!=5: raise SystemExit("BLOCKED: fewer than 5 playable dog videos")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--query",default="funny puppy")
    p.add_argument("--output",default="output/dog_pixabay_preview")
    a=p.parse_args()
    try: build(os.environ.get("PIXABAY_API_KEY"),a.output,a.query)
    except Exception as e:
        # Never leak API key in URL-bearing exceptions.
        raise SystemExit("BLOCKED: "+type(e).__name__)
if __name__=="__main__":main()
