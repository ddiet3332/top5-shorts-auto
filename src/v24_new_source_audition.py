#!/usr/bin/env python3
"""V24 exact-source Pexels audition: novel box jump, toy pounce, cat play.

3 individual official downloads at most. Clips are muted 5s SOURCE PREVIEWS.
No automated humor scoring, license sign-off, YouTube uploading, or Pexels
page scraping. Does not claim footage is Creative Commons.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from v12_sources import validate_catalog
from v12_pexels_audition import audition


PREVIOUS_POOR_SOURCES={"PX-17462877","PX-6187151","PX-7680667","PX-5495527","PX-9208508","PX-13358977"}


def checked_catalog(path: Path):
    raw=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw,list) or len(raw)!=3:
        raise ValueError("Only three individually page-reviewed high-res originals per audit")
    if any(r.get("provider")!="pexels" for r in raw):
        raise ValueError("Only the official Pexels download method is supported")
    ids=[r.get("id") for r in raw]
    if len(set(ids))!=3 or set(ids) & PREVIOUS_POOR_SOURCES:
        raise ValueError("No duplicates or previously low-payoff V21 originals")
    groups={r.get("action_group") for r in raw}
    if len(groups)!=3:
        raise ValueError("Three distinct action categories for the V24 source audition")
    for r in raw:
        if (r.get("individual_page_checked") is not True
            or r.get("license_review_status")!="provider_terms_only"
            or r.get("source_audio_approved") is not False
            or r.get("publication_approved") is not False):
            raise ValueError("Provider-level license and no-publication status required")
    return validate_catalog(raw)


def report_audition(rows, outcome, out: Path):
    by_id={x["id"]:x for x in outcome}
    result=[]
    for row in rows:
        item=by_id.get(row["id"],{})
        if item.get("editorial_status")=="VIDEO_READY_FOR_HUMAN_REVIEW":
            status="PREVIEW_CREATED_HUMOR_NOT_VERIFIED"
        else:
            status="PREVIEW_UNAVAILABLE_NO_RIGHTS_OR_DOWNLOAD_CLAIM"
        windows=item.get("windows",[])
        result.append({
            "id":row["id"],"title":row["title"],"creator_metadata":row.get("creator",""),
            "action_group":row["action_group"],"original_page":row["page_url"],
            "source_license_label":"Pexels License (provider terms; not Creative Commons)",
            "license_page":row["license_url"],"source_license_independently_cleared":False,
            "human_original_owner_confirmation":False,
            "explicit_third_party_rights_cleared":False,
            "actual_video_watched":False,"publication_approved":False,
            "status":status,
            "preview_count":len(windows),
            "windows":[{"start_sec":p.get("source_time_sec"),
                        "preview_file":p.get("preview_file"),
                        "action_humor_verified":False} for p in windows],
            "failure_code":item.get("failure_code"),
            "failure_type":item.get("failure_type")
        })
    manifest={
        "schema_version":1,"mode":"V24_RIGHTS_AWARE_NEW_ACTION_AUDITION",
        "status":"WAITING_FOR_ACTUAL_VIDEO_EDITORIAL_QA",
        "source_count":len(result),
        "previewable_originals":sum(x["preview_count"]>0 for x in result),
        "preview_count":sum(x["preview_count"] for x in result),
        "final_content_score":None,
        "publication_approved":False,
        "notices":[
            "A 5-second preview is not a confirmed funny/payoff moment.",
            "Pexels free-use terms do not prove third-party music, releases or YouTube monetization.",
            "The V23 completed-video editorial score remains 81/100 until a NEW edited 30s video is actually inspected."
        ],
        "candidates":result
    }
    (out/"V24_NEW_SOURCE_AUDIT.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# V24 — weak-rank replacement candidate review","",
        f"- Individual Pexels pages: **{len(result)}**",
        f"- Actually downloaded originals with muted previews: **{manifest['previewable_originals']}**",
        f"- 5-second previews: **{manifest['preview_count']}**",
        "- Actually verified laugh/surprise: **0 — not human inspected yet**",
        "- Rights/monetization clearance: **not granted**",
        "- 30-second V24 finished edit: **not produced by this audition**",""]
    for x in result:
        md+=[f"## {x['id']} — {x['title']}",
             f"Page: {x['original_page']}",
             f"Creator displayed: {x['creator_metadata']}",
             f"Action group: {x['action_group']}",
             f"Status: {x['status']}",
             f"Failure class: {x.get('failure_code') or x.get('failure_type') or 'none'}",
             f"Five-second previews: {', '.join(p['preview_file'] for p in x['windows']) or 'none'}",
             "Actual fun/hook and any third-party rights: **unverified**",""]
    (out/"V24_NEW_SOURCE_QA.md").write_text("\n".join(md),encoding="utf-8")
    return manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",default="sample/v24-new-candidates.json")
    p.add_argument("--output",default="output")
    args=p.parse_args()
    rows=checked_catalog(Path(args.catalog))
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    records=audition(rows,out/"V24_PREVIEWS",max_candidates=3)
    summary=report_audition(rows,records,out)
    print(f"V24 source audition: {summary['previewable_originals']}/3 source previews available,"
          f" {summary['preview_count']} total windows; no auto approvals")


if __name__=="__main__":
    main()
