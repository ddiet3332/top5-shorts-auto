"""Gate the editorial pipeline on actual media evidence, not green CI status."""
from __future__ import annotations
import argparse
import json
import hashlib
from pathlib import Path

def assess(report, required=6):
    rows=report.get("results",[])
    qualified=[]
    for row in rows:
        if row.get("technical_pass") is not True or not all(row.get(k) for k in ("local_path","duration_sec","width","height","sha256")):
            continue
        source=Path(row["local_path"])
        if not source.is_file() or not source.stat().st_size:
            continue
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if digest!=row["sha256"]:
            continue
        qualified.append(row)
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
