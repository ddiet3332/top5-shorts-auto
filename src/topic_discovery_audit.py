#!/usr/bin/env python3
"""Topic discovery audit. Records source-metadata counts, never grants rights."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from top5_auto_v30 import discover_for_topic

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--topics", default="sample/top5_auto_topics_v30.json")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--output", default="output/topic_run/DISCOVERY_AUDIT.json")
    args=ap.parse_args()
    topics=json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic=next((x for x in topics if x["topic_id"]==args.topic),None)
    if topic is None:
        raise SystemExit("Unknown topic: "+args.topic)
    candidates,errors=discover_for_topic(topic,discover=True)
    audit={"topic":args.topic,"search_phrases":topic.get("search",[]),
           "candidate_count":len(candidates),"minimum_required":5,
           "candidate_titles":[x["title"] for x in candidates[:40]],
           "source_pages":[x.get("source_page") for x in candidates[:40]],
           "errors":errors,"rights_verified":False,
           "publication_approved":False,
           "status":"READY_FOR_DOWNLOAD_CHECK" if len(candidates)>=5 else "INSUFFICIENT_CANDIDATES"}
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"topic":args.topic,"candidates":len(candidates),"status":audit["status"]}),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
