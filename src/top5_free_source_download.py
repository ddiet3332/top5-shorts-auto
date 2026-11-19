#!/usr/bin/env python3
"""Download five genuine Pixabay source clips and inspect technical integrity.
No automatic editorial score, rights clearance, or publication approval.
"""
import argparse,collections,hashlib,json,os,subprocess,urllib.parse,urllib.request
from pathlib import Path
from pixabay_dog_preview import download,probe
from top5_topic_relevance_gate import topic_metadata_match

def fetch_hits(key,query):
 params=urllib.parse.urlencode({"key":key,"q":query,"per_page":80,"safesearch":"true"})
 req=urllib.request.Request("https://pixabay.com/api/videos/?"+params,headers={"User-Agent":"TOP5FreeSourceQA/1.0"})
 with urllib.request.urlopen(req,timeout=40) as response:return json.load(response).get("hits",[])
def decode(path):
 subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-map","0:v:0","-f","null","-"],check=True,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def creator_allowed(creator,counts,max_per_creator=2):
 """Do not let one uploader dominate a five-source TOP5 video."""
 return bool(creator) and counts[creator]<max_per_creator
def obvious_topic_mismatch(tags, topic):
 """Conservative negative filter: reject obvious lexical false positives, not approve footage."""
 tags=str(tags or "").lower()
 topic=str(topic or "")
 if "비눗방울" in topic:
  if any(x in tags for x in ("bubble-headed fly", "bladder-headed fly", "fly art", "insect", "confetti", "wallpaper", "backdrop", "bokeh")):
   return True
  if not any(x in tags for x in ("soap bubble", "soap bubbles", "blowing bubbles", "bubble blowing", "frozen soap")):
   return True
 return False

def inspect(key,plan,out,fetch=fetch_hits,rejected=None):
 out.mkdir(parents=True,exist_ok=True)
 rejected=set(rejected or []);selected=plan["selected"];seen=set();rows=[];failures=[];creator_counts=collections.Counter();skipped_same_creator=0;query_counts=collections.Counter();attempted=set()
 for query in list(selected["search_queries"])+list(selected["search_queries"]):
  if len(rows)>=5:break
  # First pass distributes sources across queries; second pass fills any shortfall.
  first_pass=sum(query_counts.values())<5 and not all(q in attempted for q in selected["search_queries"])
  max_this_query=3 if first_pass and len(selected["search_queries"])>1 else 5
  attempted.add(query)
  try:hits=fetch(key,query)
  except Exception as e:failures.append({"query":query,"reason":type(e).__name__});continue
  for hit in hits:
   if len(rows)>=5 or query_counts[query]>=max_this_query:break
   ident=hit.get("id");tags=str(hit.get("tags") or "").lower();creator=str(hit.get("user") or "").strip()
   if not isinstance(ident,int) or ident in seen or ident in rejected:continue
   if not topic_metadata_match(tags,[query]):continue
   if obvious_topic_mismatch(tags,selected["topic"]):continue
   seen.add(ident)
   if not creator_allowed(creator,creator_counts):
    skipped_same_creator+=1
    continue
   if any(x in tags for x in ("cartoon","animation","animated","cgi","illustration","3d render","motion graphics","motion graphic","ai generated","ai-generated","artificial intelligence","generative ai")):continue
   if float(hit.get("duration") or 0)<5.3:continue
   variants=hit.get("videos") or {}
   video=next((variants.get(k) for k in ("medium","small","large") if (variants.get(k) or {}).get("url")),None)
   if not video:continue
   path=out/("source_%d.mp4"%ident)
   try:
    download(video["url"],path,max_bytes=35*1024*1024)
    if probe(path)<5.2:raise ValueError("short_download")
    decode(path)
    creator_counts[creator]+=1
    query_counts[query]+=1
    rows.append({"id":ident,"provider":"pixabay","query":query,"page_url":hit.get("pageURL"),"tags":hit.get("tags"),"creator":hit.get("user"),"duration_sec":round(probe(path),2),"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"full_video_decode":True,"editorial_score":None,"rights_verified":False,"publication_approved":False})
   except Exception as e:
    failures.append({"id":ident,"reason":type(e).__name__});path.unlink(missing_ok=True)
 report={"topic":selected["topic"],"category":selected["category"],"status":"DOWNLOADED_5_TECHNICALLY_VALID_SOURCES_REVIEW_ONLY" if len(rows)==5 else "BLOCKED_INSUFFICIENT_DOWNLOADED_SOURCES","downloaded_valid_sources":len(rows),"max_sources_per_creator":2,"creator_counts":dict(creator_counts),"query_counts":dict(query_counts),"rejected_source_ids":sorted(rejected),"skipped_creator_limit_or_missing":skipped_same_creator,"sources":rows,"failures":failures[:20],"editorial_score":None,"rights_verified":False,"publication_approved":False,"final_video_created":False}
 (out/"SOURCE_DOWNLOAD_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--output",default="output/top5_source_qa");p.add_argument("--rejections",default="review/rejected_source_ids.json");a=p.parse_args()
 key=os.environ.get("PIXABAY_API_KEY")
 if not key:raise SystemExit("BLOCKED_NO_PIXABAY_API_KEY")
 try:
  plan=json.loads(Path(a.plan).read_text())
  registry_path=Path(a.rejections)
  registry=json.loads(registry_path.read_text()) if registry_path.is_file() else {}
  rejected=registry.get(plan["selected"]["topic"],[])
  if not isinstance(rejected,list) or any(type(x) is not int for x in rejected):raise ValueError("Invalid rejected source IDs")
  r=inspect(key,plan,Path(a.output),rejected=rejected)
 except Exception as e:raise SystemExit("BLOCKED_SOURCE_QA_ERROR: "+type(e).__name__)
 print(json.dumps({"status":r["status"],"downloaded_valid_sources":r["downloaded_valid_sources"]}))
 if r["downloaded_valid_sources"]!=5:raise SystemExit("BLOCKED_INSUFFICIENT_DOWNLOADED_SOURCES")
if __name__=="__main__":main()
