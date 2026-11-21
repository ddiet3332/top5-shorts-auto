"""Exact-source, observed-frame review captions for TOP5; no title-only claims.

V49 original 15 + rendered 35 frames supported three nature captions.
Never project a caption onto another download, source offset or topic.
Full action verification, copyright, 85/100 editorial and YPP remain false.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STORIES=ROOT/"review/top5_reviewed_action_stories.json"

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):
            h.update(part)
    return h.hexdigest()

def apply_reviewed_captions(topic,items,out,registry=STORIES):
    out=Path(out)
    rows=json.loads(Path(registry).read_text(encoding="utf-8"))
    stories=rows.get("stories",[])
    if not isinstance(stories,list):
        raise ValueError("MALFORMED_REVIEWED_STORY_REGISTRY")
    selected=[]
    audit=[]
    for index,item in enumerate(items):
        item=dict(item)
        source=Path(item["local_path"])
        if not source.is_file():
            raise ValueError("REVIEWED_STORY_SOURCE_MISSING")
        digest=sha256(source)
        rank=5-index
        matches=[
            row for row in stories
            if row.get("topic_id")==topic.get("topic_id")
            and row.get("title")==item.get("title")
            and row.get("source_page")==item.get("source_page")
            and row.get("sha256")==digest
            and row.get("original_rank")==rank
            and abs(float(row.get("start_sec",-999))-float(item.get("cut_start",-998)))
                <=float(row.get("cut_tolerance_sec",0.12))
        ]
        if len(matches)>1:
            raise ValueError("DUPLICATE_EXACT_STORY_CAPTION_MATCH")
        if matches:
            source_row=matches[0]
            if (source_row.get("rights_verified") is not False or
                source_row.get("publication_approved") is not False or
                source_row.get("full_action_verified") is not False):
                raise ValueError("STORY_CAPTION_CANNOT_GRANT_RIGHTS_OR_ACTION_CLEARANCE")
            seq=source_row.get("caption_sequence")
            seconds=source_row.get("seconds")
            if (not isinstance(seq,list) or not 1<=len(seq)<=3
                or int(seconds) not in (4,5,6)):
                raise ValueError("INVALID_REVIEWED_STORY_TIMELINE")
            offsets=[float(x[0]) for x in seq]
            if (offsets[0]<0 or any(b-a<.65 for a,b in zip(offsets,offsets[1:]))
                or seconds-offsets[-1]<.65
                or any(not isinstance(x[1],str) or not x[1].strip()
                       or len(x[1])>38 for x in seq)):
                raise ValueError("INVALID_REVIEWED_STORY_CAPTION")
            # Do not overwrite stronger actual video-dependent edits for cats
            # and never infer this model output is owner verified.
            item["caption_sequence"]=seq
            item["caption"]=seq[0][1]
            item["label"]=item.get("label") if item.get("label") not in (
                "장면 내용 검수 필요","사물 장면 검수 필요","자연 장면 검수 필요",
                "사람 장면 검수 필요") else "실제 장면 확인"
            item["caption_source_review"]="EXACT_SHA_AND_CUT_35_PLUS_15_FRAMES"
            item["action_story_fully_verified"]=False
            item["rights_verified"]=False
            item["publication_approved"]=False
            status="SAMPLED_SCENE_CAPTION_GROUNDED"
        else:
            status="NO_EXACT_VERIFIED_CAPTION_RETAIN_REVIEW_LABEL"
        selected.append(item)
        audit.append({"rank":rank,"title":item.get("title"),
                      "original_source_sha256":digest,"cut_start":item.get("cut_start"),
                      "status":status,"rights_verified":False,
                      "whole_action_and_humor_certified":False,"publication_approved":False})
    out.mkdir(parents=True,exist_ok=True)
    report={"schema_version":1,"topic":topic.get("topic_id"),
            "sample_grounded_caption_ranks":[r["rank"] for r in audit
                  if r["status"]=="SAMPLED_SCENE_CAPTION_GROUNDED"],
            "unmatched_caption_ranks":[r["rank"] for r in audit
                  if r["status"]!="SAMPLED_SCENE_CAPTION_GROUNDED"],
            "five_ranks_story_verified":False,
            "editorial_score_100":None,
            "rights_verified":False,"youtube_reuse_verified":False,
            "publication_approved":False,"rows":audit}
    (out/"TOP5_REVIEWED_CAPTIONS_QA.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return selected,report
