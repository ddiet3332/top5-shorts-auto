"""Rank actual Commons inventory for manual review; never certify copyright.

This only produces a download shortlist. It does not download or approve files.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

EXCLUDE=("compilation","movie","film","trailer","missile","prairie dog",
         "hot dog","donut","parade","factory","animation","animated",
         "documentary","meat trade","investigation","creamery")

def shortlist(inventory, limit=20):
    rows=[]
    for item in inventory.get("candidates",[]):
        title=str(item.get("title") or "").lower()
        mime=item.get("mime")
        url=str(item.get("download_url") or "")
        if mime not in ("video/webm","video/ogg","video/mp4") or not url.startswith("https://upload.wikimedia.org/"):
            continue
        if any(term in title for term in EXCLUDE):
            continue
        if not re.search(r"\b(dog|dogs|puppy|puppies|shepherd|retriever|labrador|goldendoodle|chien)\b",title):
            continue
        if not item.get("license_url") or not item.get("creator_raw_html"):
            continue
        size=item.get("size_bytes")
        if type(size) is not int or size<=0 or size>125*1024*1024:
            continue
        label=str(item.get("license_raw") or "").lower()
        if not any(token in label for token in ("cc by","cc0","public domain")):
            continue
        item=dict(item)
        item["shortlist_status"]="REQUIRES_MEDIA_PROBE_AND_PER_FILE_RIGHTS_REVIEW"
        rows.append(item)
    rows.sort(key=lambda x:(not any(k in x["title"].lower() for k in ("playing","jump","trick","fetch","funny")),x["size_bytes"]))
    return {"status":"UNAPPROVED_SHORTLIST","count":min(len(rows),limit),
            "eligible_metadata_candidates":len(rows),"candidates":rows[:limit]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--limit",type=int,default=20)
    a=p.parse_args()
    result=shortlist(json.loads(Path(a.input).read_text(encoding="utf-8")),a.limit)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"count":result["count"],
                      "eligible_metadata_candidates":result["eligible_metadata_candidates"]}))
if __name__=="__main__":
    main()
