#!/usr/bin/env python3
"""Three-provider dog metadata discovery; rights fail closed, no source download."""
import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
from pixabay_dog_inventory import collect as pixabay_collect

def fetch_json(url, headers=None, opener=urllib.request.urlopen):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":"TOP5DogReview/1.0"})
    with opener(req,timeout=35) as resp:
        return json.load(resp)

def pexels_collect(key,query,fetch=fetch_json):
    if not key:
        return {"status":"SKIPPED_NO_SECRET","candidates":[]}
    url="https://api.pexels.com/videos/search?"+urllib.parse.urlencode({"query":query,"per_page":20})
    data=fetch(url,{"Authorization":key,"User-Agent":"TOP5DogReview/1.0"})
    return {"status":"METADATA_ONLY","candidates":[{
        "provider":"pexels","id":v.get("id"),"page_url":v.get("url"),
        "duration":v.get("duration"),"creator":(v.get("user") or {}).get("name"),
        "video_files":v.get("video_files", []),
        "tags":"","approved_for_publication":False
    } for v in data.get("videos",[])]}

def commons_collect(query,fetch=fetch_json):
    params=urllib.parse.urlencode({"action":"query","format":"json","formatversion":2,
        "generator":"search","gsrsearch":query+" filetype:video","gsrnamespace":6,
        "gsrlimit":30,"prop":"imageinfo","iiprop":"url|mime|extmetadata"})
    data=fetch("https://commons.wikimedia.org/w/api.php?"+params)
    rows=[]
    for p in data.get("query",{}).get("pages",[]):
        infos=p.get("imageinfo") or []
        if not infos: continue
        i=infos[0]
        if not (str(i.get("mime","")).startswith("video/")): continue
        meta=i.get("extmetadata") or {}
        license_url=(meta.get("LicenseUrl") or {}).get("value","")
        rows.append({"provider":"wikimedia","id":p.get("pageid"),"title":p.get("title"),
            "page_url":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(p.get("title","").replace(" ","_")),
            "license_url":license_url,"approved_for_publication":False})
    return {"status":"METADATA_ONLY","candidates":rows}

def aggregate(pools):
    candidates=[]
    seen=set()
    for provider,result in pools.items():
        for item in result.get("candidates",[]):
            key=(provider,str(item.get("id") or item.get("page_url")))
            if key in seen: continue
            seen.add(key)
            row=dict(item)
            row.update({"rights_verified":False,"likeness_verified":False,
                        "youtube_reuse_verified":False,"approved_for_publication":False})
            candidates.append(row)
    return {"status":"REVIEW_ONLY_NOT_PUBLISHABLE",
            "provider_status":{k:{"status":v.get("status"),"count":len(v.get("candidates",[]))}
                               for k,v in pools.items()},
            "candidates":candidates,"qualified_source_count":0,"publication_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--query",default="funny puppy")
    p.add_argument("--output",default="output/THREE_PROVIDER_DOG_REVIEW.json")
    args=p.parse_args()
    pools={}
    for provider,fn in (
        ("pexels",lambda:pexels_collect(os.environ.get("PEXELS_API_KEY"),args.query)),
        ("pixabay",lambda:pixabay_collect(os.environ.get("PIXABAY_API_KEY"),args.query)),
        ("wikimedia",lambda:commons_collect(args.query))):
        try:
            pools[provider]=fn()
        except Exception as e:
            # Do not print exception details; provider URLs may contain secrets.
            pools[provider]={"status":"ERROR_"+type(e).__name__,"candidates":[]}
    report=aggregate(pools)
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for k,v in report["provider_status"].items():
        print(k,v["status"],v["count"])
    print("Qualified real originals: 0 (not yet independently checked). Publication BLOCKED.")
if __name__=="__main__": main()
