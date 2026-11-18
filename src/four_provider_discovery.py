"""Four-provider dog video discovery. Inventory is NOT rights or publication approval.

Pexels/Pixabay official APIs require existing API keys; no scraping or key bypass.
Each provider fails independently and produces a normalized, deduplicated inventory.
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES=("dog playing","puppy funny","dog jumping","dog surprised")
def _get(url,headers=None):
    req=urllib.request.Request(url,headers={"User-Agent":"Top5ShortsAuto/0.1","Accept":"application/json",**(headers or {})})
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)
def pexels(key,fetch=_get):
    if not key: return {"status":"SKIP_MISSING_API_KEY","candidates":[]}
    rows=[]
    for q in QUERIES:
        url="https://api.pexels.com/v1/videos/search?"+urllib.parse.urlencode({"query":q,"per_page":25,"orientation":"portrait"})
        data=fetch(url,{"Authorization":key})
        for v in data.get("videos",[]):
            files=[f for f in v.get("video_files",[]) if f.get("file_type")=="video/mp4" and min(f.get("width") or 0,f.get("height") or 0)>=720]
            if not files: continue
            author=v.get("user") or {}
            rows.append({"provider":"pexels","id":str(v["id"]),"source_url":v.get("url"),"creator":author.get("name"),"license_url":"https://www.pexels.com/license/","duration_sec":v.get("duration"),"video_url":files[0].get("link"),"rights_verified":False,"publication_approved":False})
    return {"status":"DISCOVERY_ONLY","candidates":rows}
def pixabay(key,fetch=_get):
    if not key: return {"status":"SKIP_MISSING_API_KEY","candidates":[]}
    rows=[]
    for q in QUERIES:
        url="https://pixabay.com/api/videos/?"+urllib.parse.urlencode({"key":key,"q":q,"category":"animals","per_page":25,"safesearch":"true"})
        data=fetch(url)
        for v in data.get("hits",[]):
            files=v.get("videos") or {}
            f=next((files.get(k) for k in ("large","medium") if files.get(k) and min(files[k].get("width") or 0,files[k].get("height") or 0)>=720),None)
            if not f: continue
            rows.append({"provider":"pixabay","id":str(v["id"]),"source_url":v.get("pageURL"),"creator":v.get("user"),"license_url":"https://pixabay.com/service/license-summary/","duration_sec":v.get("duration"),"video_url":f.get("url"),"rights_verified":False,"publication_approved":False})
    return {"status":"DISCOVERY_ONLY","candidates":rows}
def run(commons,archive,pexels_key=None,pixabay_key=None,pexels_reader=pexels,pixabay_reader=pixabay):
    providers={}
    for name,existing in (("wikimedia_commons",commons),("internet_archive",archive)):
        rows=existing.get("candidates",[])
        providers[name]={"status":existing.get("status","UNKNOWN"),"count":len(rows)}
    all_rows=[]
    for name,existing in (("wikimedia_commons",commons),("internet_archive",archive)):
        for row in existing.get("candidates",[]):
            all_rows.append({"provider":name,**row,"rights_verified":False,"publication_approved":False})
    for name,reader,key in (("pexels",pexels_reader,pexels_key),("pixabay",pixabay_reader,pixabay_key)):
        try:
            result=reader(key)
            rows=result.get("candidates",[])
            providers[name]={"status":result["status"],"count":len(rows)}
            all_rows.extend(rows)
        except (OSError,ValueError,KeyError,TimeoutError) as exc:
            providers[name]={"status":"PROVIDER_ERROR","error":type(exc).__name__,"count":0}
    unique={}
    for row in all_rows:
        identifier=str(row.get("source_url") or row.get("source_page") or row.get("id") or "")
        if identifier: unique.setdefault((row["provider"],identifier),row)
    return {"status":"FOUR_PROVIDER_DISCOVERY_ONLY_NOT_RIGHTS_APPROVED","providers":providers,"count":len(unique),"candidates":list(unique.values()),"publication_approved":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--commons",required=True);p.add_argument("--archive",required=True);p.add_argument("--output",required=True)
    args=p.parse_args()
    result=run(json.loads(Path(args.commons).read_text()),json.loads(Path(args.archive).read_text()),os.environ.get("PEXELS_API_KEY"),os.environ.get("PIXABAY_API_KEY"))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"count":result["count"],"providers":result["providers"]}))
if __name__=="__main__":main()
