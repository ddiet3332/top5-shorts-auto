#!/usr/bin/env python3
"""Bounded alternate edit, technical verification only; never auto-publish."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path("output/v32_dog_final_candidate")
def read(name):
    try:return json.loads((root/name).read_text())
    except (OSError,ValueError):return {}
metrics=read("FREE_VISUAL_METRICS.json")
original=read("SELECTED_SOURCE_PROVENANCE.json").get("selected",[])
report={"attempted":False,"reason":None,"alternate_video":None,"new_sha256":None,
        "technical_pass":False,"editorial_80_verified":False,
        "rights_verified":False,"youtube_upload_permitted":False}
if len(original)!=5:
    report["reason"]="Five original provenance entries required"
else:
    # Bounded automatic improvement: try two real-source permutations and
    # retain all evidence. A passing decode is not an editorial score.
    report["attempted"]=True
    report["attempts"]=[]
    report["selection_basis"]="automatic frame-change proxy; not semantic editorial score"
    main=root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
    main_hash=hashlib.sha256(main.read_bytes()).hexdigest() if main.is_file() else None
    for variant in (1,2,3):
        alt=Path(f"output/v32_dog_alternate_candidate_{variant}")
        env=os.environ.copy()
        env["TOP5_REPAIR_VARIANT"]=str(variant)
        attempt={"variant":variant,"technical_pass":False}
        try:
            subprocess.run([sys.executable,"src/top5_auto_v32.py","--topic","dog_surprises",
                            "--output",str(alt)],env=env,check=True,timeout=900)
            video=alt/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
            if not video.is_file(): raise RuntimeError("Alternate MP4 missing")
            subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(video),
                            "-map","0:v:0","-map","0:a:0","-f","null","-"],
                           check=True,timeout=180)
            provenance=json.loads((alt/"SELECTED_SOURCE_PROVENANCE.json").read_text())["selected"]
            if len(provenance)!=5 or len({r["sha256"] for r in provenance})!=5:
                raise RuntimeError("Alternate provenance invalid")
            digest=hashlib.sha256(video.read_bytes()).hexdigest()
            if digest==main_hash: raise RuntimeError("Identical to main candidate")
            # Generate candidate-specific frame evidence for every rendered variant.
            frame_dir=alt/"FRAME_REVIEW"
            subprocess.run([sys.executable,"src/top5_qa_frames.py","--video",str(video),
                            "--output",str(frame_dir),"--count","15"],check=True,timeout=180)
            from top5_free_visual_metrics import analyze
            visual=analyze(frame_dir/"FRAME_REVIEW_MANIFEST.json",
                           alt/"FREE_VISUAL_METRICS.json")
            attempt.update({"technical_pass":True,"video":str(video),"sha256":digest,
                            "visual_change_pair_ratio":visual["visual_change_pair_ratio"],
                            "very_similar_adjacent_pairs":visual["very_similar_adjacent_pairs"]})

        except (subprocess.CalledProcessError,subprocess.TimeoutExpired,RuntimeError,OSError,ValueError) as ex:
            attempt["reason"]=type(ex).__name__+": "+str(ex)[:200]
        report["attempts"].append(attempt)
    passing=[a for a in report["attempts"] if a["technical_pass"]]
    baseline={"variant":0,"video":str(main),"sha256":main_hash,
              "visual_change_pair_ratio":float(metrics.get("visual_change_pair_ratio") or 0),
              "very_similar_adjacent_pairs":int(metrics.get("very_similar_adjacent_pairs") or 99)}
    # Close the feedback loop: assess every candidate, then choose by
    # actual visible editorial evidence when the configured reviewer is available.
    candidates=[baseline]+passing
    for candidate in candidates:
        target=Path(candidate["video"])
        evidence=target.parent/"SEMANTIC_EDITORIAL_REVIEW.json"
        if target.is_file():
            try:
                subprocess.run([sys.executable,"src/top5_semantic_review.py",
                                str(target),str(evidence)],check=True,timeout=180)
                assessment=json.loads(evidence.read_text())
                candidate["semantic_status"]=assessment.get("status","UNVERIFIED")
                candidate["visible_total"]=assessment.get("visible_total")
                candidate["visible_max"]=assessment.get("visible_max")
                candidate["weaknesses"]=assessment.get("weaknesses",[])
                candidate["recommended_repairs"]=assessment.get("recommended_repairs",[])
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError,ValueError) as ex:
                candidate["semantic_status"]="REVIEW_ERROR"
                candidate["semantic_error"]=str(ex)[:200]
    reviewed=[c for c in candidates if c.get("semantic_status")=="PARTIAL_VISION_REVIEW"
              and isinstance(c.get("visible_total"),(int,float))]
    if reviewed:
        ranked=sorted(candidates,key=lambda a:(
            -(a.get("visible_total") if isinstance(a.get("visible_total"),(int,float)) else -1),
            -a["visual_change_pair_ratio"],a["very_similar_adjacent_pairs"],a["variant"]))
        report["selection_basis"]="AI visible-editorial score, with motion proxy tie-break"
    else:
        ranked=sorted(candidates,key=lambda a:(
            -a["visual_change_pair_ratio"],a["very_similar_adjacent_pairs"],a["variant"]))
        report["selection_basis"]="motion proxy fallback: semantic review unavailable"
    # This is a bounded, auditable repair cycle. It does not certify full 80/100.
    winner=ranked[0]
    report.update({"technical_pass":bool(passing),
                   "selected_variant":winner["variant"],
                   "selected_candidate":winner["video"],
                   "selected_sha256":winner["sha256"],
                   "candidate_comparison":ranked,
                   "editorial_score_100":None,
                   "editorial_80_verified":False,
                   "automatic_quality_proxy_only":not bool(reviewed),
                   "semantic_feedback_applied":bool(reviewed),
                   "attempt_count":len(report["attempts"])})
    if not passing:
        report["reason"]="All bounded alternate edits failed technical verification"
    elif winner["variant"]!=0:
        report.update({"alternate_video":winner["video"],"new_sha256":winner["sha256"]})
(root/"AUTO_ALTERNATE_EDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
print(json.dumps(report,ensure_ascii=False))
