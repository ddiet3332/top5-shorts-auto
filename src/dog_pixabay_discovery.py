"""Pixabay dog-video discovery. No API key or download URLs are persisted."""
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
import time

API = "https://pixabay.com/api/videos/"
QUERIES = ("funny dog", "playful puppy", "dog trick")

def discover_pixabay(api_key, *, fetch=None, per_page=10, max_results=18, excluded_ids=()):
    if not api_key:
        return {"status":"NO_API_KEY","provider":"pixabay","candidates":[],"publication_approved":False}
    if not 3 <= per_page <= 20 or not 1 <= max_results <= 36:
        raise ValueError("DISCOVERY_LIMIT_EXCEEDED")
    if fetch is None:
        def fetch(url):
            req=urllib.request.Request(url,headers={
                "Accept":"application/json",
                "User-Agent":"TOP5-Editorial-Review/1.0"})
            with urllib.request.urlopen(req, timeout=18) as response:
                return json.load(response)
    seen = set(str(x) for x in excluded_ids)
    rows, errors = [], []
    for query in QUERIES:
        url = API + "?" + urllib.parse.urlencode({"key":api_key,"q":query,"per_page":per_page,"page":1,"safesearch":"true"})
        try:
            payload = fetch(url)
            for hit in payload.get("hits", []):
                vid = hit.get("id")
                if not isinstance(vid,int) or str(vid) in seen:
                    continue
                seen.add(str(vid))
                duration = hit.get("duration")
                if not isinstance(duration,(int,float)) or not 5.25 <= duration <= 120:
                    continue
                page = hit.get("pageURL","")
                if not isinstance(page,str) or not page.startswith("https://pixabay.com/videos/"):
                    continue
                videos = hit.get("videos") or {}
                chosen = next((videos.get(k) for k in ("medium","small","large","tiny")
                               if isinstance(videos.get(k),dict) and videos[k].get("url")),None)
                if not chosen:
                    continue
                rows.append({"id":f"PB-{vid}","provider":"pixabay","source_url":page,
                             "creator":str(hit.get("user",""))[:120],
                             "license_url":"https://pixabay.com/service/license-summary/",
                             "duration_sec":duration,"width":chosen.get("width"),"height":chosen.get("height"),
                             "discovery_query":query,"editorial_score":None,"semantic_review":"UNVERIFIED",
                             "reviewed_frames":False,"rights_status":"UNVERIFIED",
                             "publication_approved":False,"status":"DISCOVERED_NOT_DOWNLOADED"})
                if len(rows)>=max_results:
                    break
        except urllib.error.HTTPError as exc:
            errors.append({"query":query,"error":"HTTP_ERROR","http_status":exc.code})
            if exc.code in (401,403,429):
                break  # Do not repeat authentication/authorization/rate-limit failures.
        except (ValueError,OSError,TimeoutError,KeyError,TypeError) as exc:
            errors.append({"query":query,"error":type(exc).__name__})
        if len(rows)>=max_results:
            break
    status = ("CANDIDATES_FOUND" if rows else
              "API_REQUEST_FAILED" if errors and (len(errors) == len(QUERIES) or
                  any(e.get("http_status") in (401,403,429) for e in errors)) else
              "SOURCE_SHORTAGE")
    return {"status":status,
            "provider":"pixabay","candidates":rows,"errors":errors,"publication_approved":False}


def cached_pixabay(api_key, cache_path, *, force=False, now=None, discover=None):
    """Reuse public search metadata for 24h; never cache credentials or media URLs.

    A manual dispatch may force a new probe after an API-key correction.
    """
    if not api_key:
        return {"status":"NO_API_KEY","provider":"pixabay","candidates":[],
                "errors":[],"publication_approved":False,"cache_status":"NO_API_KEY"}
    cache_path=Path(cache_path)
    instant=time.time() if now is None else float(now)
    if not force and cache_path.is_file():
        try:
            cached=json.loads(cache_path.read_text(encoding="utf-8"))
            age=instant-float(cached["created_at"])
            payload=cached["result"]
            if 0<=age<86400 and isinstance(payload,dict) and payload.get("provider")=="pixabay" and isinstance(payload.get("candidates"),list):
                return {**payload,"cache_status":"REUSED_24H"}
        except (OSError,ValueError,TypeError,KeyError):
            pass
    discover=discover or discover_pixabay
    result=discover(api_key)
    cache_path.parent.mkdir(parents=True,exist_ok=True)
    cache_path.write_text(json.dumps({"created_at":instant,"result":result},ensure_ascii=False)+"\n",encoding="utf-8")
    return {**result,"cache_status":"REFRESHED"}

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--cache-file",type=Path)
    parser.add_argument("--force-refresh",action="store_true")
    args=parser.parse_args()
    excluded=set()
    for filename in ("sample/top5_dog_source_catalog.json","sample/dog_replacement_audition.json"):
        file=Path(filename)
        if file.exists():
            data=json.loads(file.read_text(encoding="utf-8"))
            for key in ("sources","candidates"):
                for item in data.get(key,[]):
                    sid=str(item.get("id",""))
                    if sid.startswith("PB-") and sid[3:].isdigit():
                        excluded.add(sid[3:])
    api_key=os.environ.get("PIXABAY_API_KEY","")
    if args.cache_file:
        result=cached_pixabay(api_key,args.cache_file,force=args.force_refresh,
               discover=lambda key: discover_pixabay(key,excluded_ids=excluded))
    else:
        result=discover_pixabay(api_key,excluded_ids=excluded)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PIXABAY_DISCOVERY",result["status"],"count",len(result["candidates"]),
          "cache",result.get("cache_status","DISABLED"))
    if args.cache_file and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as stream:
            stream.write("fetched="+str(result.get("cache_status")=="REFRESHED").lower()+"\n")
    for issue in result.get("errors", []):
        print("PIXABAY_REQUEST_ERROR",issue.get("query"),issue.get("error"),issue.get("http_status","unknown"))

if __name__=="__main__":
    main()
