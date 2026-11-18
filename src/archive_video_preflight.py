"""Preflight Internet Archive items using per-item metadata, not search hits."""
import argparse
import json
from collections import Counter
import re
import urllib.parse
import urllib.request
from pathlib import Path

VIDEO_EXT=(".mp4",".webm",".mov",".m4v",".ogv")
GOOD_LICENSE=("creativecommons.org/licenses/by/","creativecommons.org/publicdomain/zero/")
BAD_TITLE=("hot dog","watch dogs","prairie dog","dog park","dog shelter","dog food","dog show","dog training lecture","council","meeting","news","podcast","twitch","gameplay","movie trailer","funny or die","sesame street","wegman dogs","kills","murder","president","politics","flaherty","rotary","shooting","crime","death")
DOG_WORD=re.compile(r"\b(dog|dogs|puppy|puppies|canine|pup)\b",re.I)
MAX_SIZE=125*1024*1024

def preflight_item(identifier, opener=urllib.request.urlopen):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}",identifier) or ".." in identifier:
        return {"id":identifier,"status":"REJECT_INVALID_ID"}
    url="https://archive.org/metadata/"+urllib.parse.quote(identifier)
    request=urllib.request.Request(url,headers={"User-Agent":"Top5ShortsAuto/0.1 (GitHub ddiet3332/top5-shorts-auto)","Accept":"application/json"})
    try:
        with opener(request,timeout=25) as response:
            payload=json.load(response)
    except (OSError,ValueError,TimeoutError) as exc:
        return {"id":identifier,"status":"DEFER_METADATA_ERROR","error":type(exc).__name__}
    md=payload.get("metadata") or {}
    title=str(md.get("title") or "")
    license_url=md.get("licenseurl") or ""
    if isinstance(license_url,list): license_url=license_url[0] if license_url else ""
    license_url=str(license_url).lower()
    creator=md.get("creator")
    if not DOG_WORD.search(title) or any(x in title.lower() for x in BAD_TITLE):
        return {"id":identifier,"status":"REJECT_IRRELEVANT_TITLE","title":title}
    if not creator or not any(license_url.startswith("https://"+x) or license_url.startswith("http://"+x) for x in GOOD_LICENSE):
        return {"id":identifier,"status":"REJECT_INCOMPLETE_LICENSE_CREATOR","title":title}
    files=[]
    for f in payload.get("files") or []:
        name=str(f.get("name") or "")
        try: size=int(f.get("size") or 0)
        except (TypeError,ValueError): continue
        if not name.lower().endswith(VIDEO_EXT) or not 0<size<=MAX_SIZE: continue
        if f.get("source")!="original": continue
        if "/" in name or "\\" in name or ".." in name: continue
        files.append({"name":name,"size":size,"download_url":"https://archive.org/download/"+urllib.parse.quote(identifier)+"/"+urllib.parse.quote(name)})
    return {"id":identifier,"status":"PREFLIGHT_METADATA_ONLY_PENDING_DOWNLOAD_AND_RIGHTS" if files else "REJECT_NO_BOUNDED_ORIGINAL_VIDEO",
            "title":title,"creator":creator,"license_url":license_url,"files":files,
            "rights_verified":False,"publication_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--max-items",type=int,default=50)
    args=p.parse_args()
    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    results=[preflight_item(x["id"]) for x in data.get("candidates",[])[:max(0,min(args.max_items,60))]]
    qualified=[x for x in results if x["status"]=="PREFLIGHT_METADATA_ONLY_PENDING_DOWNLOAD_AND_RIGHTS"]
    rejection_counts=dict(sorted(Counter(x["status"] for x in results).items()))
    result={"status":"PREFLIGHT_ONLY_NOT_RIGHTS_APPROVAL","checked":len(results),"metadata_qualified":len(qualified),"status_counts":rejection_counts,"results":results}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"checked":result["checked"],"metadata_qualified":result["metadata_qualified"],"status_counts":result["status_counts"]}))
if __name__=="__main__": main()
