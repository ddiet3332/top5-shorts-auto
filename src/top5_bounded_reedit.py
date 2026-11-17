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
elif not metrics.get("possible_static_or_repetitive_visuals"):
    report["reason"]="No static/repetitive visual warning; no blind rerender"
else:
    # Bounded automatic improvement: try two real-source permutations and
    # retain all evidence. A passing decode is not an editorial score.
    report["attempted"]=True
    report["attempts"]=[]
    main=root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
    main_hash=hashlib.sha256(main.read_bytes()).hexdigest() if main.is_file() else None
    for variant in (1,2):
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
            attempt.update({"technical_pass":True,"video":str(video),"sha256":digest})
            if not report["technical_pass"]:
                report.update({"technical_pass":True,"alternate_video":str(video),
                               "new_sha256":digest,"selected_variant":variant})
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired,RuntimeError,OSError,ValueError) as ex:
            attempt["reason"]=type(ex).__name__+": "+str(ex)[:200]
        report["attempts"].append(attempt)
    if not report["technical_pass"]:
        report["reason"]="Both bounded alternate edits failed technical verification"
(root/"AUTO_ALTERNATE_EDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10))
print(json.dumps(report,ensure_ascii=False))
