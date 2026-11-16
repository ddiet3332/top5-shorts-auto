#!/usr/bin/env python3
"""Dog source audition adapted from the proven V37 cat workflow.

Download only manually specified official Pexels pages, inspect actual frames,
and fail closed for editorial and third-party rights approval.
"""
import json
from pathlib import Path
from v37_cat_audition import get_info, sheets
from v12_sources import allowed_page
from v12_pexels_audition import download_single_pexels

OUT=Path("output/dog_audition")
SOURCES=[
 {"id":"dog-frisbee","provider":"pexels","title":"A Dog Catching a Frisbee","page_url":"https://www.pexels.com/video/a-dog-catching-a-frisbee-7080033/","creator":"Brixiv","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-fetch","provider":"pexels","title":"Close-Up Shot of a Dog Playing Fetch","page_url":"https://www.pexels.com/video/close-up-shot-of-a-dog-playing-fetch-4171485/","creator":"Magda Ehlers","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-puppy","provider":"pexels","title":"A Dog Playing Catch","page_url":"https://www.pexels.com/video/a-dog-playing-catch-7515923/","creator":"RDNE Stock project","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-snow","provider":"pexels","title":"Border Collie Catching Frisbee in Snow","page_url":"https://www.pexels.com/video/border-collie-catching-frisbee-in-snow-35235651/","creator":"Michal Petráš","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-frisbee-2","provider":"pexels","title":"Dog Catching a Frisbee","page_url":"https://www.pexels.com/video/dog-catching-a-frisbee-6564028/","creator":"Brixiv","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"}
]
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=[]
 for src in SOURCES:
  row={**src,"publication_approved":False,"rights_verified":False,"actual_action_verified":False}
  path=OUT/(src["id"]+".mp4")
  try:
   if not allowed_page(src): raise ValueError("Invalid individual official source page")
   row["download"]=download_single_pexels(src,path,max_bytes=125*1024*1024)
   row.update(get_info(path))
   if row["duration_sec"]<6.2 or min(row["width"],row["height"])<360:
    row["status"]="REJECTED_TECHNICAL"
   else:
    row["frames"]=sheets(path,src["id"],OUT,row["duration_sec"])
    row["status"]="AWAITING_EDITORIAL_FRAME_REVIEW"
  except Exception as exc:
   row["status"]="FAILED"
   row["error"]=type(exc).__name__
   row["error_detail"]=str(exc)[:140]
  rows.append(row)
  print(row["id"],row["status"],flush=True)
 (OUT/"DOG_AUDITION.json").write_text(json.dumps({"publication_approved":False,"candidates":rows},ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
