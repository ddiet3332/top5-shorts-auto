#!/usr/bin/env python3
"""V37 expanded visual audition: original source frames, no automatic rights approval."""
import json
import subprocess
from pathlib import Path
from v36_cat_audition import cmd,get_info,sheets,OUTPUT as _unused
from top5 import fetch_json,download_video
from v12_sources import allowed_page
from v12_pexels_audition import download_single_pexels
from top5 import clean_html
OUTPUT=Path("output/v37_audition")
SOURCES=[
 {"id":"commons-door","provider":"commons","title":"File:Cat opening door.webm","license_required":"by-sa/4.0",
  "page_url":"https://commons.wikimedia.org/wiki/File:Cat_opening_door.webm"},
 {"id":"pexels-mirror","provider":"pexels","title":"Tabby cat checks out mirror",
  "page_url":"https://www.pexels.com/video/a-cat-is-looking-at-itself-in-a-mirror-20728739/",
  "creator":"Sueda Dilli","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"pexels-sunlit-cats","provider":"pexels","title":"Playful Cats in Sunlit Room Interaction",
  "page_url":"https://www.pexels.com/video/playful-cats-in-sunlit-room-interaction-30074573/",
  "creator":"Muhammad Khawar Nazir","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"pexels-tree-climb","provider":"pexels","title":"Curious Cat Climbing a Tree in Summer",
  "page_url":"https://www.pexels.com/video/curious-cat-climbing-a-tree-in-summer-35457158/",
  "creator":"Zeynep Coşkun","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"pexels-orange-play","provider":"pexels","title":"Playful Interaction with Orange Cat Outdoors",
  "page_url":"https://www.pexels.com/video/playful-interaction-with-orange-cat-outdoors-28715071/",
  "creator":"Zeki Binici","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
]
def commons_download(src,target):
    data=fetch_json({"action":"query","format":"json","formatversion":"2","titles":src["title"],
        "prop":"imageinfo","iiprop":"url|size|mime|extmetadata"})
    page=(data.get("query",{}).get("pages") or [])[0]
    assert page["title"]==src["title"]
    info=(page.get("imageinfo") or [])[0]
    md=info["extmetadata"]
    url=clean_html(md.get("LicenseUrl",{}).get("value","")).replace("http:","https:").rstrip("/")
    if not url.endswith(src["license_required"]):
        raise ValueError("License not matching CC BY-SA 4.0 as audited")
    author=clean_html(md.get("Artist",{}).get("value",""))
    if not author: raise ValueError("Author blank")
    direct=info["url"]
    assert direct.startswith("https://upload.wikimedia.org/")
    assert int(info.get("size",0))<60000000
    import urllib.request
    request=urllib.request.Request(direct,headers={"User-Agent":"TOP5ShortsDraft/1.0 (https://github.com/ddiet3332/top5-shorts-auto; research)"})
    with urllib.request.urlopen(request,timeout=120) as f,target.open("wb") as o:
        count=0
        while True:
            chunk=f.read(1024*1024)
            if not chunk: break
            count+=len(chunk)
            if count>60000000: raise ValueError("oversized")
            o.write(chunk)
    return {"author":author,"license":"CC BY-SA 4.0","license_url":url,
        "license_obligation":"Attribution and ShareAlike for adapted contribution",
        "source_page":src["page_url"]}
def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    results=[]
    for src in SOURCES:
        row=dict(src)
        row.update({"publication_approved":False,"provenance_confirmed":False,
            "youtube_reused_content_approved":False,"visual_strength_approved":False})
        path=OUTPUT/(src["id"]+(".webm" if src["provider"]=="commons" else ".mp4"))
        try:
            if src["provider"]=="commons":
                row.update(commons_download(src,path))
            else:
                assert allowed_page({**src,"id":src["id"]}),"Not official individual Pexels source"
                row["provider_video_info"]=download_single_pexels(src,path,max_bytes=125*1024*1024)
            row.update(get_info(path))
            if row["duration_sec"]<6.2 or min(row["width"],row["height"])<360:
                row["status"]="REJECTED_TECHNICAL"
            else:
                row["frames"]=sheets(path,src["id"],OUTPUT,row["duration_sec"])
                row["status"]="AWAITING_EDITORIAL_FRAME_REVIEW"
        except Exception as ex:
            row["status"]="FAILED"
            row["error"]=type(ex).__name__
            row["error_detail"]=str(ex)[:140]
        results.append(row)
        print(row["id"],row["status"],flush=True)
    (OUTPUT/"V37_AUDITION.json").write_text(json.dumps({
       "selected":False,"publication_approved":False,"rights_approved":False,
       "candidates":results},ensure_ascii=False,indent=2)+"\n")
    if not any(r["status"]=="AWAITING_EDITORIAL_FRAME_REVIEW" for r in results):
        raise RuntimeError("No reviewed candidate videos")
if __name__=="__main__":main()
