#!/usr/bin/env python3
"""Free Pixabay metadata preflight for ranked TOP5 topics. No footage claims."""
import argparse,json,os,re,sys
from pathlib import Path
from pixabay_dog_inventory import collect
REJECT=re.compile(r"(?<![a-z])(cartoon|animation|animated|cgi|render|illustration|ai.generated)(?![a-z])",re.I)
def evaluate(plan,key):
 selected=plan["selected"];queries=selected.get("search_queries",[])
 results=[];seen=set();errors=[]
 for query in queries:
  try: inventory=collect(key,query)
  except Exception as e:
   errors.append({"query":query,"error_type":type(e).__name__});continue
  for item in inventory["candidates"]:
   ident=item.get("id");tags=str(item.get("tags") or "")
   if not isinstance(ident,int) or ident in seen or REJECT.search(tags):continue
   if not item.get("has_video_variant") or float(item.get("duration") or 0)<5.3:continue
   seen.add(ident);results.append(item)
 return {"topic":selected["topic"],"category":selected["category"],"queries":queries,"metadata_candidates":len(results),"eligible_for_download":len(results)>=5,"video_downloaded":False,"video_created":False,"editorial_score":None,"rights_verified":False,"publication_approved":False,"candidate_metadata":results[:30],"query_errors":errors,"status":"METADATA_PREFLIGHT_ONLY" if len(results)>=5 else "BLOCKED_INSUFFICIENT_METADATA"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--output",default="output/topic_footage_preflight.json");a=p.parse_args()
 key=os.environ.get("PIXABAY_API_KEY")
 if not key:sys.exit("BLOCKED_NO_PIXABAY_API_KEY")
 plan=json.loads(Path(a.plan).read_text())
 report=evaluate(plan,key);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:report[k] for k in ("status","topic","metadata_candidates","eligible_for_download")},ensure_ascii=False))
 if not report["eligible_for_download"]:sys.exit("BLOCKED_INSUFFICIENT_METADATA")
if __name__=="__main__":main()
