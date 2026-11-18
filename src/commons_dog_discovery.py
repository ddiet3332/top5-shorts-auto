"""Discover real Wikimedia Commons dog videos; never invent rights evidence.

Discovery is a candidate inventory, not a Gate0 pass or license approval.
All results retain their original Commons file page and raw metadata.
"""
from __future__ import annotations
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

API="https://commons.wikimedia.org/w/api.php"

def discover(query="dog", limit=30):
    params=urllib.parse.urlencode({
        "action":"query","generator":"search","gsrsearch":f"filetype:video {query}",
        "gsrnamespace":"6","gsrlimit":str(min(max(limit,1),50)),
        "prop":"imageinfo","iiprop":"url|size|mime|extmetadata",
        "format":"json","formatversion":"2"})
    req=urllib.request.Request(API+"?"+params,headers={
        "User-Agent":"Top5ShortsAuto/0.1 (research; no automatic publication)",
        "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as response:
        payload=json.load(response)
    candidates=[]
    for page in payload.get("query",{}).get("pages",[]):
        info=(page.get("imageinfo") or [{}])[0]
        mime=str(info.get("mime",""))
        if not mime.startswith("video/"):
            continue
        meta=info.get("extmetadata") or {}
        def field(key):
            return str((meta.get(key) or {}).get("value") or "")
        candidates.append({
            "id":str(page.get("pageid","")),
            "provider":"wikimedia_commons",
            "title":page.get("title"),
            "source_url":info.get("descriptionurl"),
            "download_url":info.get("url"),
            "size_bytes":info.get("size"),
            "mime":mime,
            "creator_raw_html":field("Artist"),
            "license_raw":field("LicenseShortName"),
            "license_url":field("LicenseUrl"),
            "attribution_raw_html":field("Attribution"),
            "usage_terms_raw_html":field("UsageTerms"),
            "gate_0_passed":False,
            "rights_verified":False,
            "publication_approved":False,
            "reject_code":"NEEDS_PER_FILE_RIGHTS_AND_VIDEO_METADATA_REVIEW"
        })
    return {"status":"DISCOVERY_ONLY_NOT_RIGHTS_APPROVED",
            "query":query,"count":len(candidates),"candidates":candidates}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--query",default="dog")
    parser.add_argument("--limit",type=int,default=30)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=discover(args.query,args.limit)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"count":result["count"]}))
if __name__=="__main__":
    main()
