"""Mixkit dog-video LICENSE-CLASS RESEARCH only (not automatic download/rights clearance).

Per-asset Free and Restricted licenses coexist at the same provider. This
module rejects unknown/restricted clips for commercial editorial scouting and
does not assert YouTube monetization or clear third-party/music/person rights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

OFFICIAL_FREE_LICENSE = "https://mixkit.co/license/modal/videoFree/"
EXACT_FREE_LABEL = "Mixkit Stock Video Free License"
EXACT_RESTRICTED_LABEL = "Mixkit Restricted License - 720p free version for personal use only"


def screen_catalog(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("scope") != "research_only_commercial_license_screen":
        raise ValueError("INVALID_MIXKIT_CATALOG")
    if data.get("publication_approved") is not False:
        raise ValueError("MIXKIT_PREAPPROVAL_FORBIDDEN")
    if data.get("official_license_reference") != OFFICIAL_FREE_LICENSE:
        raise ValueError("LICENSE_PROVENANCE_MISMATCH")
    sources=data.get("sources")
    if not isinstance(sources,list) or not 1 <= len(sources) <= 15:
        raise ValueError("INVALID_SOURCE_LIST")
    ids=set()
    admissible=[]
    blocked=[]
    for row in sources:
        if not isinstance(row,dict) or row.get("provider") != "mixkit":
            raise ValueError("INVALID_PROVIDER")
        sid=row.get("id")
        source=row.get("source_url","")
        page=urlsplit(str(source))
        if not isinstance(sid,str) or not re.fullmatch(r"MK-[0-9]{1,9}",sid):
            raise ValueError("INVALID_MIXKIT_ID")
        if sid in ids:
            raise ValueError("DUPLICATE_MIXKIT_SOURCE")
        ids.add(sid)
        if (page.scheme!="https" or page.hostname!="mixkit.co" or page.query or page.fragment
            or not re.fullmatch(r"/free-stock-video/[a-z0-9-]+-"+sid[3:]+r"/?", page.path)):
            raise ValueError("UNTRUSTED_MIXKIT_PAGE")
        if row.get("rank_target") not in ("rank5","rank2"):
            raise ValueError("INVALID_RANK_TARGET")
        if (row.get("original_download_verified") is not False
                or row.get("semantic_review")!="UNVERIFIED"
                or row.get("publication_approved") is not False):
            raise ValueError("UNREVIEWED_MIXKIT_SOURCE_MUST_FAIL_CLOSED")
        cls=row.get("license_class")
        if cls=="FREE" and row.get("official_page_license_text")==EXACT_FREE_LABEL:
            if row.get("rights_status")!="UNVERIFIED":
                raise ValueError("FREE_NOT_RIGHTS_CLEARANCE")
            admissible.append({
                "id":sid,"provider":"mixkit","source_url":source,
                "title":row.get("title"),"rank_target":row["rank_target"],
                "action_family_hypothesis":row.get("action_family_hypothesis"),
                "license_class":"FREE",
                "eligible_for_commercial_license_screen":True,
                "metadata_review":"OFFICIAL_PAGE_FREE_LICENSE_CLAIM",
                "download_status":"NOT_ATTEMPTED",
                "semantic_review":"UNVERIFIED","rights_status":"UNVERIFIED",
                "editorial_score":None,"publication_approved":False
            })
        else:
            blocked.append({
                "id":sid,"reason":"MIXKIT_RESTRICTED_OR_UNVERIFIED_LICENSE",
                "publication_approved":False})
    return {"schema_version":1,"provider":"mixkit",
            "status":"FREE_LICENSE_PAGES_FOUND" if admissible else "NO_CLEARED_CLASS",
            "free_license_page_candidates":admissible,
            "commercially_blocked":blocked,
            "preview_count":0,"publication_approved":False,
            "next_action":"VERIFY_OFFICIAL_MEDIA_DOWNLOAD_AND_VISUAL_PAYOFF",
            "note":"Free license page classification is not proof of content ownership or video monetization."}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",type=Path,default=Path("sample/dog_mixkit_license_screen_v1.json"))
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    result=screen_catalog(a.catalog)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DOG_MIXKIT_LICENSE_SCREEN",result["status"],
          "free_pages",len(result["free_license_page_candidates"]),
          "restricted",len(result["commercially_blocked"]),flush=True)


if __name__=="__main__":
    main()
