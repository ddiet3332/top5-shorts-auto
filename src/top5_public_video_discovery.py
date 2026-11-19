#!/usr/bin/env python3
"""Public Wikimedia Commons and Internet Archive video discovery.
Metadata-only: never equate search hits with licensed, reviewed source clips.
"""
import argparse,json,re,urllib.parse,urllib.request
from pathlib import Path

UA="TOP5-Shorts-Research/1.0 (public video metadata; manual rights review)"
VIDEO_EXT=(".webm",".ogv",".ogg",".mp4",".mov",".m4v")
PERMISSIVE={"cc0","public domain","pd","cc by","cc by-sa","cc-by","cc-by-sa"}
def request_json(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=35) as response:return json.load(response)
def clean(value):
 return re.sub(r"<[^>]+>"," ",str(value or "")).strip()
def license_flag(short_name):
 name=clean(short_name).lower().replace("_"," ").strip()
 return "LICENSE_CANDIDATE_REVIEW_REQUIRED" if any(name==p or name.startswith(p+" ") or name.startswith(p+"-") for p in PERMISSIVE) else "LICENSE_UNKNOWN_OR_RESTRICTED"
def commons(query,fetch=request_json):
 params={"action":"query","format":"json","generator":"search","gsrsearch":query+" filetype:video","gsrnamespace":6,"gsrlimit":20,"prop":"imageinfo","iiprop":"url|mime|size|extmetadata","iilimit":1}
 data=fetch("https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(params))
 result=[]
 for page in (data.get("query") or {}).get("pages",{}).values():
  info=(page.get("imageinfo") or [{}])[0];meta=info.get("extmetadata") or {}
  title=page.get("title","");url=info.get("url","")
  if not title.lower().endswith(VIDEO_EXT) or not url.startswith("https://"):continue
  lic=clean((meta.get("LicenseShortName") or {}).get("value"))
  result.append({"provider":"wikimedia","id":str(page.get("pageid")),"title":title,"file_url":url,"page_url":info.get("descriptionurl"),"mime":info.get("mime"),"bytes":info.get("size"),"license":lic,"license_url":clean((meta.get("LicenseUrl") or {}).get("value")),"artist":clean((meta.get("Artist") or {}).get("value"))[:250],"license_gate":license_flag(lic),"rights_verified":False,"editorial_verified":False})
 return result
def archive(query,fetch=request_json):
 params={"q":"mediatype:movies AND ("+query+")","fl[]":["identifier","title","licenseurl"],"rows":12,"page":1,"output":"json"}
 # urlencode doseq preserves repeated field names
 data=fetch("https://archive.org/advancedsearch.php?"+urllib.parse.urlencode(params,doseq=True))
 result=[]
 for doc in (data.get("response") or {}).get("docs",[]):
  ident=doc.get("identifier")
  if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}",ident):continue
  try:meta=fetch("https://archive.org/metadata/"+urllib.parse.quote(ident))
  except Exception:continue
  metadata=meta.get("metadata") or {};lic=metadata.get("licenseurl") or doc.get("licenseurl") or ""
  if isinstance(lic,list):lic=lic[0] if lic else ""
  for file in meta.get("files") or []:
   name=file.get("name","")
   if not name.lower().endswith(VIDEO_EXT):continue
   if str(file.get("source","")).lower()=="derivative":continue
   url="https://archive.org/download/"+urllib.parse.quote(ident)+"/"+urllib.parse.quote(name,safe="/")
   flag="LICENSE_CANDIDATE_REVIEW_REQUIRED" if "creativecommons.org/licenses/by" in str(lic).lower() or "creativecommons.org/publicdomain/" in str(lic).lower() else "LICENSE_UNKNOWN_OR_RESTRICTED"
   artist=metadata.get("creator") or ""
   if isinstance(artist,list):artist=", ".join(str(x) for x in artist)
   result.append({"provider":"internet_archive","id":ident+":"+name,"title":doc.get("title") or metadata.get("title"),"file_url":url,"page_url":"https://archive.org/details/"+ident,"license":str(lic),"license_url":str(lic),"artist":artist,"license_gate":flag,"rights_verified":False,"editorial_verified":False})
   break
 return result
def discover(queries,fetch=request_json):
 results=[];errors=[]
 for query in queries[:4]:
  for provider,fn in (("wikimedia",commons),("internet_archive",archive)):
   try:
    for item in fn(query,fetch):item["query"]=query;results.append(item)
   except Exception as exc:errors.append({"provider":provider,"query":query,"error":type(exc).__name__})
 seen=set();unique=[]
 for row in results:
  key=(row["provider"],row["id"])
  if key not in seen:seen.add(key);unique.append(row)
 return {"status":"METADATA_ONLY_NOT_CLEARED_FOR_DOWNLOAD_OR_PUBLISHING","candidate_count":len(unique),"candidates":unique[:80],"errors":errors,"rights_verified":False,"source_video_decoded":False,"publication_approved":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--output",default="output/top5_external_sources/DISCOVERY.json");a=p.parse_args()
 plan=json.loads(Path(a.plan).read_text());report=discover(plan["selected"]["search_queries"]);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({"status":report["status"],"candidate_count":report["candidate_count"],"errors":report["errors"]},ensure_ascii=False))
if __name__=="__main__":main()
