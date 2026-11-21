"""Narrow human-supervised rank repair for the exact V56 five-source cohort.

Sources may change after rediscovery; only all five exact SHA+URL+cut
matches authorize repositioning. Unseen footage is never re-ranked
based on title. Ranking is a *relative editorial preference*, not
performance evidence, 85/100, YPP, or copyright clearance.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"review/top5_v56_nature_rank_evidence.json"

def source_hash(path):
    d=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            d.update(block)
    return d.hexdigest()

def apply_rank_repair(topic,items,output,registry=EVIDENCE):
    output=Path(output)
    rows=[dict(row) for row in items]
    d=json.loads(Path(registry).read_text(encoding="utf-8"))
    evidence=d.get("ranked_sources",[])
    report={
      "schema_version":1,"requested_topic":topic.get("topic_id"),
      "status":"NO_EXACT_REVIEWED_COHORT_MATCH",
      "visual_relative_strength_reordered":False,
      "five_rank_source_provenance_verified":False,
      "editorial_score_100":None,
      "rights_verified":False,
      "youtube_reuse_approved":False,"publication_approved":False}
    if topic.get("topic_id")=="nature_moments" and len(rows)==5 and len(evidence)==5:
        hashes=[]
        for row in rows:
            path=Path(row.get("local_path",""))
            hashes.append(source_hash(path) if path.is_file() else None)
        desired={x["sha256"]:x for x in evidence}
        exact=(
            len(desired)==5
            and set(hashes)==set(desired)
            and len(hashes)==len(set(hashes))
            and all(
                row.get("title")==desired[digest]["title"]
                and row.get("source_page")==desired[digest]["source_page"]
                and abs(float(row.get("cut_start",-999))-
                        float(desired[digest]["cut_start"]))<=0.12
                and row.get("publication_approved") is False
                and row.get("rights_verified") is False
                for row,digest in zip(rows,hashes,strict=True))
            and {x.get("preferred_rank") for x in evidence}=={1,2,3,4,5}
            and d.get("publication_approved") is False
            and d.get("source_rights_verified") is False
        )
        if exact:
            ordered=sorted(zip(rows,hashes,strict=True),
                           key=lambda pair:-desired[pair[1]]["preferred_rank"])
            rows=[row for row,_ in ordered]
            report["status"]="EXACT_FIVE_SOURCE_RANK_REORDER_REVIEW_ONLY"
            report["visual_relative_strength_reordered"]=True
            report["five_rank_source_provenance_verified"]=True
            report["ranks"]=[
                {"rank":5-i,"previous_rank":desired[digest]["observed_rank"],
                 "sha256":digest,"original_cut_start":row["cut_start"]}
                for i,(row,digest) in enumerate(ordered)]
    output.mkdir(parents=True,exist_ok=True)
    (output/"TOP5_V57_RANK_REPAIR_QA.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return rows,report
