"""Strict human/AI review-to-render repair bridge; never treats advice as permission."""
import json
from pathlib import Path

ALLOWED={"replace_source","shift_highlight","revise_caption"}
def apply_feedback(clips,feedback):
    if not isinstance(clips,list) or len(clips)!=5: raise ValueError("five clips required")
    if not isinstance(feedback,dict) or feedback.get("schema_version")!=1: raise ValueError("feedback schema_version=1 required")
    repairs=feedback.get("repairs",[])
    if not isinstance(repairs,list) or len(repairs)>5: raise ValueError("up to five repairs")
    updated=[dict(x) for x in clips]
    report={"applied":[],"rejected":[],"rights_verified":False,"publication_approved":False}
    seen=set()
    for item in repairs:
        if not isinstance(item,dict): report["rejected"].append("invalid_item");continue
        rank=item.get("rank");action=item.get("action")
        if type(rank) is not int or rank not in range(1,6) or rank in seen or action not in ALLOWED:
            report["rejected"].append({"rank":rank,"reason":"invalid_rank_or_action"});continue
        seen.add(rank);idx=5-rank;clip=updated[idx]
        if action=="revise_caption":
            value=item.get("caption")
            if not isinstance(value,str) or not 1<=len(value)<=55:
                report["rejected"].append({"rank":rank,"reason":"invalid_caption"});continue
            clip["caption"]=value
        elif action=="shift_highlight":
            delta=item.get("delta_seconds")
            if type(delta) not in (int,float) or not -3<=delta<=3:
                report["rejected"].append({"rank":rank,"reason":"invalid_delta"});continue
            duration=float(clip.get("duration_sec",0))
            current=float(clip.get("cut_start",0))
            if duration<6.2:
                report["rejected"].append({"rank":rank,"reason":"short_source"});continue
            clip["cut_start"]=round(max(0,min(duration-6.08,current+delta)),2)
        else:
            report["rejected"].append({"rank":rank,"reason":"replace_source_requires_new_audition_not_arbitrary_url"})
            continue
        report["applied"].append({"rank":rank,"action":action})
    return updated,report

def load_and_apply(clips,path,output):
    p=Path(path)
    if not p.is_file():
        report={"status":"NO_FEEDBACK","applied":[],"rejected":[],"rights_verified":False,"publication_approved":False}
        return clips,report
    try:
        updated,report=apply_feedback(clips,json.loads(p.read_text(encoding="utf-8")))
        report["status"]="APPLIED" if report["applied"] else "NO_APPLICABLE_REPAIRS"
    except (ValueError,TypeError,KeyError) as exc:
        updated=clips
        report={"status":"INVALID_FEEDBACK","error":str(exc)[:200],"applied":[],"rights_verified":False,"publication_approved":False}
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return updated,report
