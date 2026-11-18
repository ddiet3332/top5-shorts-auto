#!/usr/bin/env python3
"""Independent technical/editorial-risk report; never grants publication approval."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
def audit(source_dir,render_dir):
 source_dir=Path(source_dir);render_dir=Path(render_dir)
 src=json.loads((source_dir/"SOURCE_DOWNLOAD_QA.json").read_text())
 render=json.loads((render_dir/"GENERIC_V06_QA.json").read_text())
 video=render_dir/render["file"]
 probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-select_streams","v:0","-show_entries","stream=width,height,r_frame_rate,nb_read_frames","-show_entries","format=duration","-of","json",str(video)],text=True))
 stream=probe["streams"][0]
 sources=src.get("sources",[])
 ids=[s.get("id") for s in sources]; hashes=[s.get("sha256") for s in sources]
 creators=[s.get("creator","unknown") for s in sources]
 counts=collections.Counter(creators)
 checks={"five_sources":len(sources)==5,"distinct_source_ids":len(set(ids))==5,"distinct_source_hashes":len(set(hashes))==5,"all_sources_decoded":all(s.get("full_video_decode") is True for s in sources),"full_25s":abs(float(probe["format"]["duration"])-25)<0.06,"portrait_1080p":(stream["width"],stream["height"])==(1080,1920),"frame_rate_24":stream["r_frame_rate"]=="24/1","frame_count_600":int(stream.get("nb_read_frames") or 0)==600,"video_sha_matches":hashlib.sha256(video.read_bytes()).hexdigest()==render.get("sha256")}
 blockers=["Visual content and ranking not independently verified","Source rights and YouTube reuse eligibility not verified","Metadata captions are not visual scene analysis"]
 if max(counts.values(),default=0)>=3:blockers.append("Source diversity: >=3 of 5 clips from same creator")
 result={"status":"TECHNICAL_PASS_EDITORIAL_REVIEW_REQUIRED" if all(checks.values()) else "TECHNICAL_FAIL","checks":checks,"source_creators":dict(counts),"source_diversity_warning":max(counts.values(),default=0)>=3,"captions":render.get("captions"),"caption_method":render.get("caption_method"),"editorial_score":None,"rights_verified":False,"rankings_verified":False,"publication_approved":False,"publication_blockers":blockers}
 (render_dir/"INDEPENDENT_REVIEW_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
 if not all(checks.values()):raise SystemExit("Technical QA failed: "+json.dumps(checks))
 return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--render",default="output/top5_v06_review");a=p.parse_args()
 print(json.dumps(audit(a.sources,a.render),ensure_ascii=False))
