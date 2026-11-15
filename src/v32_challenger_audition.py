#!/usr/bin/env python3
"""V32 two-rights-screened source challengers: sample real six-second actions.

Real video files -> six-second muted previews and eight-frame contact sheet.
No approval based on metadata, no YouTube upload, no source camera audio.
"""
from __future__ import annotations
import json,io,subprocess,urllib.parse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from top5 import fetch_json,extract_candidates,download_video,probe_duration,motion_highlight
from v12_pexels_audition import download_single_pexels

ROOT=Path("output/v32_challengers")
PEXELS={"id":"PX-40826295","provider":"pexels",
 "title":"Playful Cat Rolling on Urban Sidewalk",
 "page_url":"https://www.pexels.com/video/playful-cat-rolling-on-urban-sidewalk-40826295/",
 "creator":"Zeynep Coşkun",
 "license_label":"Pexels License",
 "license_url":"https://www.pexels.com/license/"}
COMMONS="File:Ocicat on leash climbing a tree.webm"

def get_photo(path,ts):
    cmd=["ffmpeg","-hide_banner","-v","error","-ss",str(ts),
          "-i",str(path),"-frames:v","1","-f","image2pipe",
          "-vcodec","mjpeg","-q:v","3","pipe:1"]
    raw=subprocess.run(cmd,check=True,capture_output=True,timeout=30).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")

def make_window(path,start,out):
    # 6-second source excerpt, NOT a claim that funny action is verified.
    filter_="scale=460:800:force_original_aspect_ratio=decrease:flags=lanczos,pad=460:800:(ow-iw)/2:(oh-ih)/2:color=black,fps=12,setsar=1,format=yuv420p"
    subprocess.run(["ffmpeg","-hide_banner","-v","error","-y",
        "-ss",f"{start:.2f}","-i",str(path),"-t","6",
        "-vf",filter_,"-an","-c:v","libx264",
        "-preset","veryfast","-crf","30","-movflags","+faststart",str(out)],
        check=True,timeout=95)

def contact(path,starts,out):
    cells=[]
    for start in starts:
        for t in [start+.5,start+1.5,start+2.5,start+3.5,start+4.5,start+5.5]:
            frame=get_photo(path,t)
            h=230
            w=250
            frame.thumbnail((w,h))
            tile=Image.new("RGB",(w,h),"#101010")
            tile.paste(frame,((w-frame.width)//2,(h-frame.height)//2))
            cells.append(tile)
    sheet=Image.new("RGB",(6*250,len(starts)*230),"#101010")
    for i,cell in enumerate(cells):
        sheet.paste(cell,((i%6)*250,(i//6)*230))
    sheet.save(out,quality=90)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    candidates=[]
    pexel=ROOT/"pexels_40826295.mp4"
    try:
        details=download_single_pexels(PEXELS,pexel,max_bytes=125*1024*1024)
        candidates.append({"provider":"pexels","title":PEXELS["title"],"original":str(pexel),
            "source_page":PEXELS["page_url"],"claimed_license":PEXELS["license_label"],
            "license_url":PEXELS["license_url"],"author_metadata":PEXELS["creator"],
            "duration":details["duration_sec"],"source_provenance_verified":False})
    except Exception as e:
        candidates.append({"provider":"pexels","title":PEXELS["title"],
             "status":"SOURCE_UNAVAILABLE_NOT_SELECTED","failure_type":type(e).__name__,
             "failure_safe":str(e)[:100].split("http")[0]})
        pexel.unlink(missing_ok=True)
    raw=fetch_json({"action":"query","format":"json","formatversion":"2",
       "titles":COMMONS,"prop":"imageinfo","iiprop":"url|size|mime|extmetadata"})
    rows={r["title"]:r for r in extract_candidates(raw)}
    if COMMONS in rows:
        meta=rows[COMMONS]
        dest=ROOT/"commons_tree_cat.webm"
        try:
            download_video(meta,dest)
            candidates.append({"provider":"wikimedia","title":COMMONS,
                "original":str(dest),"source_page":meta["source_page"],
                "claimed_license":meta["license"],"license_url":meta["license_url"],
                "author_metadata":meta["author"],
                "duration":probe_duration(dest),"source_provenance_verified":False})
        except Exception as e:
            candidates.append({"provider":"wikimedia","title":COMMONS,
                "status":"DOWNLOAD_FAILURE_NOT_SELECTED","failure_type":type(e).__name__})
            dest.unlink(missing_ok=True)
    else:
        candidates.append({"provider":"wikimedia","title":COMMONS,
            "status":"LICENSE_METADATA_REJECTED"})
    for row in candidates:
        if "original" not in row:continue
        path=Path(row["original"])
        dur=float(row["duration"])
        # 6-sec candidates: beginning, central strongest motion, ending
        peak,_=motion_highlight(path,dur,seconds=5)
        starts=sorted(set(round(max(0,min(x,dur-6.15)),2) for x in
                (0,float(peak),max(0,dur-6.3))))
        windows=[]
        for i,at in enumerate(starts,1):
            preview=ROOT/(path.stem+f"_window_{i}.mp4")
            make_window(path,at,preview)
            windows.append({"start":at,"preview":preview.name,
                "action_verified":False,"rights_verified":False})
        contact(path,starts,ROOT/(path.stem+"_contact.jpg"))
        row["windows"]=windows
        row["status"]="VIDEO_AUDITION_READY_RIGHTS_UNVERIFIED"
        row["publication_approved"]=False
        # remove full original from shareable artifact; preview only
        path.unlink()
        row.pop("original")
    (ROOT/"V32_CHALLENGER_QA.json").write_text(json.dumps(
        {"status":"REVIEW_ONLY","publication_approved":False,
         "new_source_independently_verified":False,
         "candidate_results":candidates},ensure_ascii=False,indent=2)+"\n",
         encoding="utf-8")
    print("AUDITION COMPLETE",[(x["title"],x["status"]) for x in candidates],flush=True)

if __name__=="__main__":main()
