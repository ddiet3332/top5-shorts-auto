"""Discover alternative dog video candidates via Internet Archive public metadata.

Discovery only. Archive metadata and CC labels are not independent rights proof.
"""
from __future__ import annotations
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

API="https://archive.org/advancedsearch.php"

def discover(query="(title:dog OR title:dogs OR title:puppy OR title:puppies) AND mediatype:movies",rows=100):
    params=urllib.parse.urlencode({"q":query,"fl[]":["identifier","title","licenseurl","creator","year"],
                                   "rows":str(min(max(rows,1),100)),"page":"1","output":"json"},doseq=True)
    request=urllib.request.Request(API+"?"+params,headers={
        "User-Agent":"Top5ShortsAuto/0.1 (research; contact via GitHub ddiet3332/top5-shorts-auto)",
        "Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=35) as response:
        payload=json.load(response)
    items=[]
    for doc in payload.get("response",{}).get("docs",[]):
        identifier=str(doc.get("identifier") or "")
        if not identifier or "/" in identifier or ".." in identifier:
            continue
        licenseurl=doc.get("licenseurl") or ""
        if isinstance(licenseurl,list):
            licenseurl=licenseurl[0] if licenseurl else ""
        title=str(doc.get("title") or "")
        if not any(word in title.lower().split() for word in ("dog","dogs","puppy","puppies")):
            continue
        items.append({"id":identifier,"title":doc.get("title"),
            "creator":doc.get("creator"),"license_url":licenseurl,
            "source_url":"https://archive.org/details/"+urllib.parse.quote(identifier),
            "metadata_url":"https://archive.org/metadata/"+urllib.parse.quote(identifier),
            "rights_verified":False,"publication_approved":False,
            "status":"DISCOVERY_ONLY_REQUIRES_PER_FILE_REVIEW"})
    return {"status":"UNAPPROVED_ALTERNATE_PROVIDER_INVENTORY","count":len(items),"candidates":items}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--rows",type=int,default=100)
    a=p.parse_args()
    try:
        result=discover(rows=a.rows)
    except (OSError,ValueError,TimeoutError) as exc:
        result={"status":"PROVIDER_UNAVAILABLE","count":0,"error":type(exc).__name__,"candidates":[]}
    target=Path(a.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"count":result["count"]}))
if __name__=="__main__":
    main()
