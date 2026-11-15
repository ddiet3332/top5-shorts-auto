#!/usr/bin/env python3
"""V34 candidate-source factual action audition (NOT final licenses approval).

Only pre-curated official Pexels download endpoints and Commons CC0/CC-BY
metadata source. The 1st-ranked existing Salto cat is sampled from source
start, mid and end to test a new no-empty-tail 6 second window.
Never downloads unvetted or restricted pages and never uses source audio.
"""
from __future__ import annotations
import io,json,subprocess
from pathlib import Path
from PIL import Image
from top5 import fetch_json,extract_candidates,download_video,probe_duration
from v12_pexels_audition import download_single_pexels
from v12_sources import allowed_page

DEST=Path("output/v34_original_review")
FILES=[
 {"id":"PX-10231519","provider":"pexels","title":"Cat Playing with Toy",
  "page_url":"https://www.pexels.com/video/cat-playing-with-toy-10231519/",
  "creator":"Peggy Anke","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"PX-6864984","provider":"pexels","title":"Playing Bait With A Pet Cat",
  "page_url":"https://www.pexels.com/video/playing-bait-with-a-pet-cat-6864984/",
  "creator":"cottonbro studio","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"PX-34689563","provider":"pexels","title":"Playful Cat Under Sofa with Toy Ball",
  "page_url":"https://www.pexels.com/video/playful-cat-under-sofa-with-toy-ball-34689563/",
  "creator":"nilay ortanca","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"}
]
COMMONS="File:Salto - Cat Jump.webm"

def frame(path,at):
    cmd=["ffmpeg","-hide_banner","-v","error","-ss",f"{at:.2f}",
          "-i",str(path),"-frames:v","1","-f","image2pipe",
          "-vcodec","mjpeg","-q:v","3","pipe:1"]
    p=subprocess.run(cmd,capture_output=True,check=True,timeout=40)
    return Image.open(io.BytesIO(p.stdout)).convert("RGB")

def audition(path,name,duration):
    # Fixed source-relative video sampler. A six-second segment cannot start
    # past the last six seconds. No reuse, reversal, synthetic animals, etc.
    if duration<6.1:raise ValueError("not enough frames for six second source")
    test=[0,max(0,(duration-6.02)/2),max(0,duration-6.03)]
    test=sorted(set(round(x,2) for x in test))
    windows=[]
    for i,start in enumerate(test):
        out=DEST/f"{name}_v{i+1}.mp4"
        vf=("scale=432:768:force_original_aspect_ratio=decrease,"
            "pad=432:768:(ow-iw)/2:(oh-ih)/2:color=black,"
            "fps=12,format=yuv420p")
        subprocess.run(["ffmpeg","-hide_banner","-v","error","-y",
            "-ss",str(start),"-i",str(path),"-t","6",
            "-vf",vf,"-an","-c:v","libx264","-preset","ultrafast",
            "-crf","30","-movflags","+faststart",str(out)],
            check=True,timeout=100)
        windows.append({"source_start_seconds":start,"preview":out.name,
                        "right_to_republish_verified":False})
    # Each row is six consecutive points across a 6sec source candidate.
    sheet=Image.new("RGB",(6*214,3*266),"#141414")
    for k,start in enumerate(test):
        for idx in range(6):
            t=min(duration-.15,start+.15+idx*.98)
            im=frame(path,t)
            im.thumbnail((214,266))
            sheet.paste(im,(idx*214+(214-im.width)//2,k*266+(266-im.height)//2))
    sheet.save(DEST/f"{name}_contact.jpg",quality=88)
    return windows

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    status=[]
    # Source already appears in V32, but we need unseen beginning to fix tail.
    data=fetch_json({"action":"query","format":"json","formatversion":"2",
       "titles":COMMONS,"prop":"imageinfo","iiprop":"url|size|mime|extmetadata"})
    allowed={x["title"]:x for x in extract_candidates(data)}
    sources=[]
    if COMMONS in allowed:
        meta=allowed[COMMONS];sources.append(("salto",COMMONS,meta))
    else:status.append({"title":COMMONS,"status":"LICENSE_FILTER_REJECTED"})
    for id,title,meta in sources:
        dest=DEST/(id+".webm")
        try:
            download_video(meta,dest)
            duration=probe_duration(dest)
            row={"title":title,"provider":"wikimedia","source":meta["source_page"],
                 "creator_claim":meta["author"],"license_claim":meta["license"],
                 "license_url":meta["license_url"],"duration":duration,
                 "windows":audition(dest,id,duration),
                 "status":"ACTUAL_VIDEO_PREVIEW_READY",
                 "original_rights_verified":False}
            status.append(row)
        except Exception as e:
            status.append({"title":title,"status":"FAILED",
                          "failure_type":type(e).__name__,"safe_note":str(e)[:100].split("http")[0]})
        finally:dest.unlink(missing_ok=True)
    for row in FILES:
        dest=DEST/(row["id"]+".mp4")
        try:
            if not allowed_page(row):raise ValueError("Incorrect original official video page")
            details=download_single_pexels(row,dest,max_bytes=125*1024*1024)
            duration=details["duration_sec"]
            status.append({"title":row["title"],"provider":"pexels",
               "source":row["page_url"],"creator_claim":row["creator"],
               "license_claim":"Pexels License","duration":duration,
               "windows":audition(dest,row["id"],duration),
               "status":"ACTUAL_VIDEO_PREVIEW_READY",
               "original_rights_verified":False})
        except Exception as e:
            status.append({"title":row["title"],"status":"FAILED",
             "failure_type":type(e).__name__,"safe_note":str(e)[:100].split("http")[0]})
        finally:dest.unlink(missing_ok=True)
    (DEST/"V34_CANDIDATE_ACTION_REVIEW.json").write_text(
      json.dumps({"publication_approved":False,
         "rights_independently_cleared":False,
         "provider_license_not_youtube_monetization":True,
         "new_clip_editorial_status":"HUMAN_FRAME_REVIEW_REQUIRED",
         "candidates":status},ensure_ascii=False,indent=2)+"\n",
         encoding="utf-8")
    print("V34",[(x["title"],x["status"]) for x in status],flush=True)

if __name__=="__main__":main()
