#!/usr/bin/env python3
"""Bridge reviewed source fingerprints to per-run captions without auto-approval.
Approved source reviews must be independently authored and committed.
"""
import argparse,json
from pathlib import Path
def build(qa,registry):
 sources=qa.get("sources",[])
 if len(sources)!=5:return {"approved":False,"reason":"NOT_FIVE_SOURCES"}
 records=registry.get("reviews",[])
 if not isinstance(records,list):return {"approved":False,"reason":"INVALID_REGISTRY"}
 matched=[]
 for source in sources:
  found=[x for x in records if x.get("sha256")==source.get("sha256") and x.get("provider")==source.get("provider") and str(x.get("source_id"))==str(source.get("id")) and x.get("topic")==qa.get("topic") and x.get("verified_by_human") is True and x.get("approved_for_render") is True]
  if len(found)!=1:return {"approved":False,"reason":"SOURCE_NOT_INDEPENDENTLY_APPROVED","source_id":source.get("id")}
  item=found[0]
  if not item.get("rights_evidence_url") or not item.get("license") or item.get("rights_reviewed") is not True:return {"approved":False,"reason":"RIGHTS_EVIDENCE_MISSING","source_id":source.get("id")}
  if item.get("scene_relevant") is not True or item.get("scene_reviewed") is not True or not str(item.get("scene_description") or "").strip():
   return {"approved":False,"reason":"SCENE_RELEVANCE_NOT_VERIFIED","source_id":source.get("id")}
  # Motion-dependent titles require independently reviewed temporal evidence.
  # A single still frame or Pixabay tag is insufficient to claim flight.
  if "비행" in str(qa.get("topic") or ""):
   if item.get("motion_reviewed") is not True or item.get("motion_matches_topic") is not True:
    return {"approved":False,"reason":"TOPIC_MOTION_NOT_VERIFIED","source_id":source.get("id")}
  if item.get("distinct_action") is not True:
   return {"approved":False,"reason":"DISTINCT_TOP5_ACTION_NOT_VERIFIED","source_id":source.get("id")}
  if item.get("third_party_rights_cleared") is not True or item.get("likeness_rights_cleared") is not True:
   return {"approved":False,"reason":"THIRD_PARTY_OR_LIKENESS_RIGHTS_UNRESOLVED","source_id":source.get("id")}
  matched.append({"source_id":source["id"],"rank_name":item.get("rank_name"),"caption":item.get("caption")})
 return {"approved":True,"topic":qa.get("topic"),"verified_by_human":True,"approved_for_render":True,"entries":matched}
def main():
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa/SOURCE_DOWNLOAD_QA.json");p.add_argument("--registry",default="review/approved_source_registry.json");p.add_argument("--output",default="reviewed_top5_captions.json");a=p.parse_args()
 qa=json.loads(Path(a.sources).read_text())
 path=Path(a.registry)
 registry=json.loads(path.read_text()) if path.is_file() else {"reviews":[]}
 result=build(qa,registry)
 if result.get("approved"):Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({"approved":result["approved"],"reason":result.get("reason","SOURCE_FINGERPRINT_MATCHED")},ensure_ascii=False))
if __name__=="__main__":main()
