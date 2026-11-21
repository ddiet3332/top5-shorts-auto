#!/usr/bin/env python3
"""Download five genuine provider source clips and inspect technical integrity.
No automatic editorial score, rights clearance, or publication approval.
"""
import argparse,collections,datetime,hashlib,json,os,re,subprocess,urllib.parse,urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
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
 if any(key in topic for key in ("댄스", "체조", "곡예")):
  # Pixabay dance search includes wildlife that happens to have 'dancing'
  # in the tags (real production #44891628808 rank 1: flamingos).
  # A human-skills episode must not silently turn into an animal TOP5.
  # Excluding animal cues is intentionally conservative; mixed scenes need
  # explicit frame review and should not enter an unreviewed human source set.
  if re.search(r"\b(flamingos?|birds?|penguins?|dogs?|puppies|cats?|kitten|monkeys?|insects?|butterflies|fish|pets?|wildlife|animals?)\b",tags):
   return True
 if "도미노" in topic:
  return not re.search(r"\bdomino(?:es|s)?\b",tags) or bool(re.search(r"\bjenga\b",tags))
 if "기계 움직임" in topic:
  machine=re.search(r"\b(machine(?:s|ry)?|gears?|engines?|robots?|pistons?)\b",tags)
  physical_context=re.search(
   r"\b(construction|agricultur(?:e|al)|manufacturing|industrial|factory|tractor|excavator|lathe|harvester|crane|milling)\b",tags)
  generated=re.search(r"\b(doodle|abstract|scoreboard|countdown|wallpaper|3d|fantasy|fractal)\b",tags)
  return not (machine and physical_context) or bool(generated)
 if "고양이" in topic and any(x in tags for x in ("sleep", "sleeping", "coziness", "cozyness", "wallpaper", "background", "cat eyes", "kitten eyes")):
  return True
 if "비눗방울" in topic:
  if any(x in tags for x in ("bubble-headed fly", "bladder-headed fly", "fly art", "insect", "confetti", "wallpaper", "backdrop", "bokeh")):
   return True
  if not any(x in tags for x in ("soap bubble", "soap bubbles", "blowing bubbles", "bubble blowing", "frozen soap")):
   return True
 return False

def inspect(key,plan,out,fetch=fetch_hits,rejected=None,*,prepare=None,extra=(),reserve=0):
 out.mkdir(parents=True,exist_ok=True)
 rejected=set(rejected or []);selected=plan["selected"];seen=set();rows=[];failures=[];creator_counts=collections.Counter();skipped_same_creator=0;query_counts=collections.Counter();attempted=set()
 cache={}
 target=5+reserve
 for query in list(selected["search_queries"])+list(selected["search_queries"]):
  if len(rows)>=target:break
  # First pass distributes sources across queries; second pass fills any shortfall.
  first_pass=sum(query_counts.values())<5 and not all(q in attempted for q in selected["search_queries"])
  max_this_query=3 if first_pass and len(selected["search_queries"])>1 else target
  attempted.add(query)
  try:
   if query not in cache:cache[query]=fetch(key,query) if key else []
   hits=cache[query]
  except Exception as e:failures.append({"query":query,"reason":type(e).__name__});continue
  for hit in hits:
   if len(rows)>=target or query_counts[query]>=max_this_query:break
   ident=hit.get("id");tags=str(hit.get("tags") or "").lower();creator=str(hit.get("user") or "").strip()
   if not isinstance(ident,int) or ident in seen or ident in rejected:continue
   if not topic_metadata_match(tags,[query]):continue
   if obvious_topic_mismatch(tags,selected["topic"]):
    seen.add(ident)
    failures.append({"id":ident,"reason":"주제의 핵심 대상을 확인할 수 없는 메타데이터"})
    continue
   seen.add(ident)
   if not creator_allowed(creator,creator_counts):
    skipped_same_creator+=1
    continue
   if any(x in tags for x in ("cartoon","animation","animated","cgi","illustration","3d render","motion graphics","motion graphic","ai generated","ai-generated","artificial intelligence","generative ai")):continue
   if float(hit.get("duration") or 0)<(6 if prepare else 5.3):continue
   variants=hit.get("videos") or {}
   video=next((variants.get(k) for k in ("medium","small","large") if (variants.get(k) or {}).get("url")),None)
   if not video:continue
   path=out/("source_%d.mp4"%ident)
   try:
    download(video["url"],path,max_bytes=35*1024*1024)
    if probe(path)<5.2:raise ValueError("short_download")
    decode(path)
    row={"id":ident,"provider":"pixabay","query":query,"page_url":hit.get("pageURL"),"tags":hit.get("tags"),"creator":creator,"duration_sec":probe(path),"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"full_video_decode":True,"editorial_score":None,"rights_verified":False,"publication_approved":False,"topic":selected["topic"],
         **evidence(video["url"],"Pixabay Content License","https://pixabay.com/service/license-summary/",False)}
    if prepare:prepare(path,row,rows)
    creator_counts[creator]+=1
    query_counts[query]+=1
    rows.append(row)
   except Exception as e:
    failures.append({"id":ident,"reason":str(e) if isinstance(e,ValueError) else type(e).__name__});path.unlink(missing_ok=True)
 if prepare and len(rows)<5:
  supplement(extra,out,prepare,rows,failures,creator_counts,query_counts,selected["topic"],target)
 report={"topic":selected["topic"],"category":selected["category"],"status":"DOWNLOADED_5_TECHNICALLY_VALID_SOURCES_REVIEW_ONLY" if len(rows)>=5 else "BLOCKED_INSUFFICIENT_DOWNLOADED_SOURCES","downloaded_valid_sources":min(len(rows),5),"max_sources_per_creator":2,"creator_counts":dict(creator_counts),"query_counts":dict(query_counts),"rejected_source_ids":sorted(rejected),"skipped_creator_limit_or_missing":skipped_same_creator,"sources":rows[:5],"reserve_sources":rows[5:],"reviewed_weak_window_rejections":sum("SOURCE_REVIEWED_WEAK_WINDOW" in str(item.get("reason", "")) for item in failures),"failures":failures[:20],"editorial_score":None,"rights_verified":False,"publication_approved":False,"final_video_created":False}
 (out/"SOURCE_DOWNLOAD_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 return report


def evidence(url, license_name, terms, attribution):
 return {"original_url":url,"license":license_name,"terms_url":terms,
         "attribution_required":attribution,"rights_status":"RIGHTS_UNVERIFIED",
         "downloaded_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}


def supplement(candidates,out,prepare,rows,failures,creators,queries,topic,target=5):
 from top5_public_video_download_probe import fetch_limited
 for index,item in enumerate(candidates):
  if len(rows)>=target or index>=30:break
  provider=item["provider"]
  if "error" in item:
   failures.append(item)
   continue
  creator=item.get("artist") or item.get("creator")
  page=item.get("page_url")
  title=item.get("title") or ""
  url=item.get("file_url") or ""
  terms=item.get("license_url") or ""
  cc=re.fullmatch(r"https?://creativecommons\.org/(?:licenses/(by(?:-sa)?)/[0-9.]+|publicdomain/(?:zero|mark)/1\.0)/?",terms)
  if not (cc or provider=="pexels") or not page or not creator_allowed(creator,creators):continue
  if not url.startswith("https://") or not topic_metadata_match(title,[item["query"]]):continue
  if obvious_topic_mismatch(title,topic):continue
  path=out/f"source_{provider}_{index}.mp4"
  try:
   fetch_limited(url,path)
   duration=probe(path)
   decode(path)
   row={"id":item["id"],"provider":provider,"page_url":page,"creator":creator,
        "duration_sec":duration,"file":path.name,"tags":title,"query":item["query"],
        "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"full_video_decode":True,"topic":topic,
        **evidence(url,item["license"],terms,bool(cc and cc[1]))}
   prepare(path,row,rows)
   creators[creator]+=1
   queries[item["query"]]+=1
   rows.append(row)
  except Exception as exc:
   failures.append({"provider":provider,"id":item["id"],
                    "reason":str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
   path.unlink(missing_ok=True)


def fallback(discovery,queries,pexels_key):
 from three_provider_dog_discovery import pexels_collect
 yield from discovery.get("errors",[])
 if pexels_key:
  for query in queries:
   try:
    pool=pexels_collect(pexels_key,query)["candidates"]
   except Exception as exc:
    yield {"provider":"pexels","query":query,"error":type(exc).__name__}
    continue
   for row in pool[:6]:
    variants=[v for v in row["video_files"] if v.get("file_type")=="video/mp4" and v.get("link")]
    if not variants:continue
    variant=min(variants,key=lambda v:abs((v.get("width") or 0)-960))
    slug=urllib.parse.urlparse(row.get("page_url") or "").path
    yield {**row,"file_url":variant["link"],"title":slug.replace("-"," "),
           "query":query,"license":"Pexels License","license_url":"https://www.pexels.com/license/"}
 yield from discovery.get("candidates",[])


def acquire(key, pexels_key, plan, out, registry, prepare, discovery, max_topics):
 """Try the planned topic and a bounded number of alternatives, keeping provenance."""
 from top5_public_video_discovery import discover
 selected = plan["selected"]
 candidates = [selected, *plan.get("alternatives", [])][:max_topics]
 attempts = []
 out.mkdir(parents=True, exist_ok=True)
 for index, candidate in enumerate(candidates):
  queries = candidate["search_queries"]
  rejected = registry.get(candidate["topic"], [])
  if not isinstance(rejected, list) or any(type(x) is not int for x in rejected):
   raise ValueError("원본 제외 목록 형식이 올바르지 않습니다")

  def extra():
   yield from fallback(discovery if index == 0 else discover(queries), queries, pexels_key)

  with TemporaryDirectory(dir=out) as folder:
   work = Path(folder)
   report = inspect(key, {**plan, "selected": candidate}, work, rejected=rejected,
                    prepare=prepare, extra=extra(), reserve=2)
   attempts.append({"topic":candidate["topic"],"status":report["status"],
                    "downloaded_valid_sources":report["downloaded_valid_sources"],
                    "failures":report["failures"]})
   if report["downloaded_valid_sources"] == 5:
    for row in [*report["sources"], *report.get("reserve_sources", [])]:
     (work / row["file"]).replace(out / row["file"])
    if index:
     plan["selected"] = {**candidate, "selection_method":"source_availability_fallback",
                         "estimated_topic_score":None}
    break
 plan["source_attempts"] = attempts
 report["topic_attempts"] = attempts
 (out/"SOURCE_DOWNLOAD_QA.json").write_text(
  json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return report


def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--output",default="output/top5_source_qa");p.add_argument("--rejections",default="review/rejected_source_ids.json");p.add_argument("--topic-attempts",type=int,choices=(1,2,3),default=1);a=p.parse_args()
 key=os.environ.get("PIXABAY_API_KEY")
 try:
  from top5_production_review import prepare_source, read, save
  plan=read(Path(a.plan))
  registry_path=Path(a.rejections)
  registry=read(registry_path) if registry_path.is_file() else {}
  discovery_path=Path("output/top5_external_sources/DISCOVERY.json")
  discovery=read(discovery_path) if discovery_path.is_file() else {}
  r=acquire(key,os.environ.get("PEXELS_API_KEY"),plan,Path(a.output),registry,
            prepare_source,discovery,a.topic_attempts)
  save(Path(a.plan),plan)
 except Exception as e:raise SystemExit("BLOCKED_SOURCE_QA_ERROR: "+type(e).__name__)
 print(json.dumps({"status":r["status"],"downloaded_valid_sources":r["downloaded_valid_sources"]}))
 if r["downloaded_valid_sources"]!=5:raise SystemExit("BLOCKED_INSUFFICIENT_DOWNLOADED_SOURCES")
if __name__=="__main__":main()
