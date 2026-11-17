#!/usr/bin/env python3
"""Evidence-only automated repair backlog. No invented editorial or rights score."""
import json
from pathlib import Path

root=Path("output/v32_dog_final_candidate")
def load(name):
    try: return json.loads((root/name).read_text(encoding="utf-8"))
    except (OSError,ValueError): return {}
qa=load("TOP5_AUTOMATED_QA_SCORE.json")
visual=load("FREE_VISUAL_METRICS.json")
diag=load("V32_BUILD_DIAGNOSTICS.json")
sources=load("SELECTED_SOURCE_PROVENANCE.json").get("selected",[])
tasks=[]
for name,passed in qa.get("technical_checks",{}).items():
    if not passed: tasks.append({"kind":"technical","check":name,"action":"Repair technical check and rerender"})
if len(sources)!=5 or len({x.get("sha256") for x in sources})!=5:
    tasks.append({"kind":"source","action":"Select five distinct playable originals"})
if visual.get("possible_static_or_repetitive_visuals"):
    tasks.append({"kind":"visual","action":"Inspect repetitive scenes and replace after frame-level review"})
for failure in diag.get("source_failures",[]):
    tasks.append({"kind":"download","source":failure.get("id"),"reason":failure.get("error"),"action":"Find and verify alternative original"})
tasks.append({"kind":"editorial","action":"Independent 7-category creative review; do not infer 85+ from technical QA"})
tasks.append({"kind":"rights","action":"Verify actual authorship, third-party rights and YouTube reused-content risks"})
report={"technical_pass":qa.get("technical_pass") is True,"technical_score":qa.get("technical_score_100"),
"source_count":len(sources),"visual_change_ratio":visual.get("visual_change_pair_ratio"),
"editorial_score":None,"editorial_85_verified":False,"rights_verified":False,
"youtube_upload_permitted":False,"automatic_rebuild_performed":False,"repair_tasks":tasks}
root.mkdir(parents=True,exist_ok=True)
(root/"AUTO_REPAIR_PLAN.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))
