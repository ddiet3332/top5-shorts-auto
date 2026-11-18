#!/usr/bin/env python3
"""AI topic planner only. Never claims a finished or rights-cleared video."""
import argparse, datetime, json, os, re, sys, urllib.request
from pathlib import Path

CATEGORIES=["people","animals","weather","nature","insects","objects"]
SYSTEM="""You plan Korean-language TOP5 short videos across people, animals, weather, nature, insects, and objects. Return ONLY JSON: {"candidates":[{"topic":"Korean specific TOP5 theme","category":"one of people,animals,weather,nature,insects,objects","search_queries":["English video search phrase","second phrase"],"hook":"Korean first-2-second hook","scores":{"curiosity":0,"impact":0,"footage":0,"distinctiveness":0,"feasibility":0}}]}. Generate 10 genuinely different topics. Scores are integers bounded by 25,25,25,15,10 respectively. Prefer observable, legal, non-exploitative scenes available in licensable stock footage. Avoid unverifiable rankings, identifying private people, graphic injury, misinformation and sensational claims. Scores are estimates, NOT evidence of available clips or predicted views."""
def generate(key,model):
    payload={"model":model,"instructions":SYSTEM,"input":"Generate 10 distinct TOP5 video topics. JSON only.","max_output_tokens":2600}
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=90) as r: data=json.load(r)
    text="".join(c.get("text","") for item in data.get("output",[]) for c in item.get("content",[]) if c.get("type")=="output_text")
    return json.loads(text)
def main():
    p=argparse.ArgumentParser();p.add_argument("--slot",choices=["AM","PM"],required=True);p.add_argument("--history",default="topic_history.json");p.add_argument("--output",default="output/topic_plan.json");a=p.parse_args()
    key=os.getenv("OPENAI_API_KEY")
    if not key: sys.exit("BLOCKED_NO_AI_KEY: AI topic selection not simulated")
    try: data=generate(key,os.getenv("TOP5_TOPIC_MODEL","gpt-4.1-mini"))
    except Exception as e: sys.exit("BLOCKED_AI_TOPIC_ERROR: "+type(e).__name__)
    history=json.loads(Path(a.history).read_text()) if Path(a.history).exists() else []
    today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
    used={x.get("topic","").strip().lower() for x in history[-100:]}
    today_categories={x.get("category") for x in history if x.get("date")==today}
    candidates=[]
    for c in data.get("candidates",[]):
        if not isinstance(c,dict):continue
        topic=str(c.get("topic","")).strip();category=c.get("category");scores=c.get("scores",{})
        if not topic or category not in CATEGORIES or topic.lower() in used or category in today_categories:continue
        if not isinstance(scores,dict):continue
        caps={"curiosity":25,"impact":25,"footage":25,"distinctiveness":15,"feasibility":10}
        if any(not isinstance(scores.get(k),int) or not 0<=scores[k]<=v for k,v in caps.items()):continue
        queries=c.get("search_queries")
        if not isinstance(queries,list) or len(queries)<2 or any(not isinstance(q,str) or not q.strip() for q in queries[:2]):continue
        candidates.append({"topic":topic,"category":category,"search_queries":queries[:3],"hook":str(c.get("hook","")),"estimated_topic_score":sum(scores.values()),"scores":scores})
    candidates.sort(key=lambda c:c["estimated_topic_score"],reverse=True)
    if not candidates:sys.exit("BLOCKED_NO_DISTINCT_AI_TOPIC")
    chosen=candidates[0]
    report={"date":today,"slot":a.slot,"status":"TOPIC_PLANNED_NOT_PRODUCED","selected":chosen,"alternatives":candidates[1:],"minimum_final_video_score":75,"source_footage_verified":False,"video_created":False,"rights_verified":False,"publication_approved":False}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({"status":report["status"],"slot":a.slot,"topic":chosen["topic"],"score":chosen["estimated_topic_score"]},ensure_ascii=False))
if __name__=="__main__":main()
