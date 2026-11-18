#!/usr/bin/env python3
"""Fail closed before render unless the five actual downloaded source IDs were reviewed."""
import argparse,json
from pathlib import Path
from top5_generic_v06_preview import load_reviewed_captions
def verify(source_dir,review_file):
 source_dir=Path(source_dir);review_file=Path(review_file)
 if not review_file.is_file():
  return {"approved":False,"reason":"REVIEW_MANIFEST_MISSING","next_action":"Inspect real source MP4s and 15-frame contact sheet; create source-matched human-reviewed captions."}
 qa=json.loads((source_dir/"SOURCE_DOWNLOAD_QA.json").read_text())
 sources=qa.get("sources",[])
 if len(sources)!=5:return {"approved":False,"reason":"NOT_FIVE_SOURCES"}
 try:
  review=json.loads(review_file.read_text())
  if review.get("topic")!=qa.get("topic"):raise ValueError("Topic mismatch")
  if review.get("approved_for_render") is not True:raise ValueError("Render not approved")
  captions=load_reviewed_captions(review_file,sources)
  if len(captions)!=5:raise ValueError("Five captions required")
  return {"approved":True,"reason":"HUMAN_REVIEWED_SOURCE_MATCHED","source_ids":[s["id"] for s in sources]}
 except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:return {"approved":False,"reason":"REVIEW_INVALID","detail":str(e)}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--review",default="reviewed_top5_captions.json");p.add_argument("--output",default="output/top5_visual_review/RENDER_GATE.json");a=p.parse_args()
 result=verify(a.sources,a.review);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False))
 if not result["approved"]:raise SystemExit("BLOCKED_REVIEW_REQUIRED")
