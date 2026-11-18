"""Gate the editorial pipeline on actual media evidence, not green CI status."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def assess(report, required=6):
    rows=report.get("results",[])
    qualified=[r for r in rows if r.get("technical_pass") is True
               and r.get("local_path") and r.get("duration_sec")
               and r.get("width") and r.get("height")]
    distinct={r["id"] for r in qualified}
    blocked=bool(report.get("provider_rate_limited"))
    return {"status":("BLOCKED_PROVIDER_RATE_LIMIT" if blocked else
                      "READY_FOR_GATE2_GATE3_AND_RIGHTS_REVIEW" if len(distinct)>=required else
                      "INSUFFICIENT_VERIFIED_MEDIA"),
            "qualified_distinct_count":len(distinct),"required":required,
            "can_render":False,"rights_verified":False,
            "reason":"Technical metadata alone does not prove clip rights, semantic value, or publication eligibility"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=assess(json.loads(Path(a.input).read_text(encoding="utf-8")))
    Path(a.output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
if __name__=="__main__":
    main()
