#!/usr/bin/env python3
"""Produce evidence-linked human-review worksheet; never auto-approve a source."""
import argparse,json
from pathlib import Path
def build(qa):
 return {"topic":qa.get("topic"),"instructions":"Inspect original video and all frame samples, independently check provider license and third-party/likeness rights. Do not mark approved without evidence.","reviews":[{"source_id":s.get("id"),"provider":s.get("provider"),"sha256":s.get("sha256"),"topic":qa.get("topic"),"source_file":s.get("file"),"source_page_url":s.get("page_url"),"metadata_tags_unverified":s.get("tags"),"contact_sheet":"TOP5_SOURCE_CONTACT_SHEET.jpg","temporal_evidence":"TOP5_TEMPORAL_9FRAMES_PER_SOURCE.jpg","motion_reviewed":False,"motion_matches_topic":False,"scene_description":"","scene_reviewed":False,"scene_relevant":False,"distinct_action":False,"rank_name":"","caption":"","license":"","rights_evidence_url":"","rights_reviewed":False,"third_party_rights_cleared":False,"likeness_rights_cleared":False,"verified_by_human":False,"approved_for_render":False} for s in qa.get("sources",[])]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa/SOURCE_DOWNLOAD_QA.json");p.add_argument("--output",default="output/top5_visual_review/SOURCE_REVIEW_WORKSHEET.json");a=p.parse_args()
 qa=json.loads(Path(a.sources).read_text());out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(build(qa),ensure_ascii=False,indent=2))
 print(json.dumps({"review_candidates":len(qa.get("sources",[])),"approved":0,"worksheet":str(out)}))
if __name__=="__main__":main()
