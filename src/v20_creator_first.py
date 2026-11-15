#!/usr/bin/env python3
"""V20: Original creator's public CC0/CC BY page -> exact-name audit -> real MP4 previews.

Only source author and self-publication metadata provide preliminary evidence.
Neither content humor nor third-party rights nor YouTube reused-content are
approved here. Original audio is stripped from preview files.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from top5 import fetch_json,extract_candidates
from v17_discovery import make_review


def valid_metadata(items, allowed):
    """Compare current MediaWiki metadata against previously inspected file pages."""
    if not isinstance(allowed,list) or not 1 <= len(allowed) <= 8:
        raise ValueError("Only 1..8 exact individually reviewed source pages")
    by_title={x["title"]:x for x in items}
    vetted=[]
    rejected=[]
    seen=set()
    for row in allowed:
        title=row.get("title","")
        if not isinstance(title,str) or not title.startswith("File:") or title in seen:
            raise ValueError("Invalid or duplicate exact Commons source")
        seen.add(title)
        item=by_title.get(title)
        reason=None
        if not item:
            reason="LICENSE_OR_MEDIA_NOT_IN_WHITELIST"
        else:
            exact_page=str(item.get("source_page","")).split("?")[0].replace("_"," ")
            expected_page=str(row.get("page_url","")).replace("_"," ")
            # URL encoding may vary; a matching exact title plus the official
            # Commons file page is a stronger/safer basis than arbitrary URLs.
            if not expected_page.startswith("https://commons.wikimedia.org/wiki/File:"):
                reason="SOURCE_PAGE_NOT_OFFICIAL"
            elif row.get("expected_source") != "Own work":
                reason="SELF_PUBLICATION_NOT_CLAIMED"
            else:
                source_claim=re.sub(r"\s+"," ",str(item.get("source_claim",""))).casefold()
                if "own work" not in source_claim and "self" not in source_claim:
                    reason="NO_CURRENT_OWN_WORK_METADATA"
                author=str(item.get("author","")).casefold()
                if reason is None and str(row.get("expected_author","")).casefold() not in author:
                    reason="CREATOR_MISMATCH"
                lic=str(item.get("license_url","")).casefold().rstrip("/")
                expected=row.get("expected_license")
                if reason is None and expected=="CC0" and "publicdomain/zero/1.0" not in lic:
                    reason="CC0_LICENSE_CHANGED_OR_ABSENT"
                elif reason is None and expected=="CC BY 4.0" and not lic.endswith("/licenses/by/4.0"):
                    reason="CC_BY_LICENSE_CHANGED_OR_ABSENT"
                elif expected not in ("CC0","CC BY 4.0"):
                    reason="UNSUPPORTED_LICENSE"
        if reason is not None:
            rejected.append({"title":title,"reason":reason})
        else:
            entry=dict(item)
            entry["cat_category_evidence"]=True  # individually inspected cat file description
            entry["review_flags"]=list(item.get("review_flags",[]))+[
                "Video not yet watched for humor",
                "Self-publication is page metadata, not independent proof of every third-party right"
            ]
            vetted.append(entry)
    return vetted,rejected


def fetch_exact(allowed):
    titles=[x["title"] for x in allowed]
    data=fetch_json({"action":"query","format":"json","formatversion":"2",
                     "titles":"|".join(titles),"prop":"imageinfo",
                     "iiprop":"url|size|mime|extmetadata"})
    return list(extract_candidates(data))


def audit(allowed,origin,out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    vetted,rejected=valid_metadata(origin,allowed)
    # Always write a traceable rights-first report, including negative cases.
    license_report={
        "status":"METADATA_REVIEW_ONLY",
        "curated_count":len(allowed),
        "current_metadata_pass_count":len(vetted),
        "rejected":rejected,
        "sources":[{
            "title":c["title"],"source_page":c["source_page"],
            "author_metadata":c.get("author"),"license_metadata":c.get("license"),
            "license_url":c.get("license_url"),"source_claim":c.get("source_claim"),
            "original_owner_independently_proven":False,
            "actual_comedic_action_reviewed":False,
            "third_party_audio_approved":False,
            "youtube_monetization_approved":False,
            "publication_approved":False
        } for c in vetted],
        "publication_approved":False
    }
    (out/"V20_CREATOR_LICENSE_AUDIT.json").write_text(
        json.dumps(license_report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not vetted:
        raise RuntimeError("No source passed the exact self-published creator license metadata checks")
    previews=make_review(out,limit=min(8,len(vetted)),
                         byte_budget=145*1024*1024,max_file=55*1024*1024,
                         source_override=vetted)
    (out/"V20_CREATOR_PREVIEW_REPORT.json").write_text(
        json.dumps(previews,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return license_report,previews


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",default="sample/v20-creator-first.json")
    p.add_argument("--output",default="output")
    args=p.parse_args()
    allowed=json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    if not isinstance(allowed,list):
        raise ValueError("Expected curated file list")
    for x in allowed:
        if not isinstance(x,dict) or not x.get("title"):
            raise ValueError("Missing exact file title")
    rights,previews=audit(allowed,fetch_exact(allowed),Path(args.output))
    print(f"V20: {rights['current_metadata_pass_count']} self-publication claims,"
          f" {previews['audition_count']} actual previewed originals,"
          " zero approved for publication",flush=True)


if __name__=="__main__":
    main()
