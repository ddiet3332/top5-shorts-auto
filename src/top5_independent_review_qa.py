#!/usr/bin/env python3
"""Independent technical/editorial-risk report; never grants publication approval."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
MIN_EDITORIAL_SCORE=75
EXCELLENT_EDITORIAL_SCORE=85
def score_decision(score,rights_verified=False,rankings_verified=False):
 """75 passes editorial threshold; rights and ranking remain hard blockers."""
 if score is None:return "NOT_SCORED"
 if isinstance(score,bool) or not isinstance(score,(int,float)) or not 0<=score<=100:raise ValueError("Score must be 0..100")
 if score<MIN_EDITORIAL_SCORE:return "REVISE_BELOW_75"
 if not rights_verified or not rankings_verified:return "EDITORIAL_PASS_PUBLICATION_BLOCKED"
 return "EDITORIAL_PASS_REVIEW_FOR_PUBLICATION"
def source_diversity_pass(creators,max_per_creator=2):
 """Fail closed if a creator is missing or supplies more than two clips."""
 return len(creators)==5 and all(isinstance(x,str) and x.strip() for x in creators) and max(collections.Counter(creators).values(),default=0)<=max_per_creator
def audit(source_dir,render_dir):
 source_dir=Path(source_dir);render_dir=Path(render_dir)
 src=json.loads((source_dir/"SOURCE_DOWNLOAD_QA.json").read_text(encoding="utf-8"))
 render=json.loads((render_dir/"GENERIC_V06_QA.json").read_text(encoding="utf-8"))
 video=render_dir/render["file"]
 probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-select_streams","v:0","-show_entries","stream=width,height,r_frame_rate,nb_read_frames","-show_entries","format=duration","-of","json",str(video)],text=True))
 stream=probe["streams"][0]
 sources=src.get("sources",[])
 evidence_path=render_dir/"RIGHTS_EVIDENCE.json"
 if render.get("timeline") and evidence_path.is_file():
  evidence=json.loads(evidence_path.read_text(encoding="utf-8"))
  sources=evidence["sources"]
  if (evidence.get("video_sha256") != render.get("sha256") or
      [row["source_sha256"] for row in render["timeline"]] != [row["sha256"] for row in sources]):
   raise SystemExit("MP4와 원본 사용 구간의 연결 검증 실패")
 hashes=[s.get("sha256") for s in sources]
 creators=[s.get("creator","unknown") for s in sources]
 counts=collections.Counter(creators)
 duration = 25 if render["file"] == "TOP5_V06_GENERIC_REVIEW_25s.mp4" else 30
 checks={"five_sources":len(sources)==5,"creator_diversity":source_diversity_pass(creators),"distinct_source_ids":len({(s.get("provider"), s.get("id")) for s in sources})==5,"distinct_source_hashes":len(set(hashes))==5,"all_sources_decoded":all(s.get("full_video_decode") is True for s in sources),"expected_duration":abs(float(probe["format"]["duration"])-duration)<0.15,"portrait_1080p":(stream["width"],stream["height"])==(1080,1920),"frame_rate_24":stream["r_frame_rate"]=="24/1","expected_frame_count":int(stream.get("nb_read_frames") or 0)==duration*24,"video_sha_matches":hashlib.sha256(video.read_bytes()).hexdigest()==render.get("sha256")}
 blockers=["Visual content and ranking not independently verified","Source rights and YouTube reuse eligibility not verified","Metadata captions are not visual scene analysis"]
 if not source_diversity_pass(creators):blockers.append("Source diversity HARD FAIL: unknown creator or more than two clips from one creator")
 score=render.get("editorial_score")
 decision=score_decision(score,render.get("rights_verified") is True,render.get("rankings_verified") is True)
 result={"minimum_editorial_score":MIN_EDITORIAL_SCORE,"excellent_reference_score":EXCELLENT_EDITORIAL_SCORE,"score_decision":decision,"status":"TECHNICAL_PASS_EDITORIAL_REVIEW_REQUIRED" if all(checks.values()) else "TECHNICAL_FAIL","checks":checks,"source_creators":dict(counts),"source_diversity_warning":not source_diversity_pass(creators),"captions":render.get("captions"),"caption_method":render.get("caption_method"),"editorial_score":score,"rights_verified":False,"rankings_verified":False,"publication_approved":False,"publication_blockers":blockers}
 (render_dir/"INDEPENDENT_REVIEW_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
 if not all(checks.values()):raise SystemExit("Technical QA failed: "+json.dumps(checks))
 return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--render",default="output/top5_v06_review");a=p.parse_args()
 print(json.dumps(audit(a.sources,a.render),ensure_ascii=False))
