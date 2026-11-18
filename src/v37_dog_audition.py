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
 {"id":"dog-frisbee-2","provider":"pexels","title":"Dog Catching a Frisbee","page_url":"https://www.pexels.com/video/dog-catching-a-frisbee-6564028/","creator":"Brixiv","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-field","provider":"pexels","title":"Energetic Dog Playing in Open Field","page_url":"https://www.pexels.com/video/energetic-dog-playing-in-open-field-35282488/","creator":"Jay's Photography","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-jump-person","provider":"pexels","title":"Dog Jumping on Woman's Back","page_url":"https://www.pexels.com/video/dog-jumping-on-woman-s-back-7628753/","creator":"ArtHouse Studio","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-bag-surprise","provider":"pexels","title":"Dog Jumping Out of a Bag","page_url":"https://www.pexels.com/video/dog-jumping-out-of-a-bag-8473589/","creator":"Cup of Couple","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-door-rush","provider":"pexels","title":"Door Opening and Dogs Running Out","page_url":"https://www.pexels.com/video/door-opening-and-dogs-running-out-11103352/","creator":"Anna Bondarenko","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-door-peek","provider":"pexels","title":"Curious Dog Peeking Around a Doorframe","page_url":"https://www.pexels.com/video/curious-dog-peeking-around-a-doorframe-31147382/","creator":"K","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-two-puppies-play","provider":"pexels","title":"Two Dogs Playing Around","page_url":"https://www.pexels.com/video/two-dogs-playing-around-5728455/","creator":"Sam Lion","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-jump-close","provider":"pexels","title":"Close up of Dogs Jumping","page_url":"https://www.pexels.com/video/close-up-of-dogs-jumping-12029012/","creator":"Anna Bondarenko","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-water-play","provider":"pexels","title":"Dog Playing with Water","page_url":"https://www.pexels.com/video/dog-playing-with-water-9006741/","creator":"Viktoria B.","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-stick-backyard","provider":"pexels","title":"Playful Dog Running in Backyard with Stick","page_url":"https://www.pexels.com/video/playful-dog-running-in-backyard-with-stick-34711078/","creator":"Kevin Early","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"},
 {"id":"dog-fetch-ring","provider":"pexels","title":"A Dog Running on the Backyard","page_url":"https://www.pexels.com/video/a-dog-running-on-the-backyard-8746627/","creator":"ROMAN ODINTSOV","license_label":"Pexels License","license_url":"https://www.pexels.com/license/"}
]
# Repeated Actions runs confirmed these sources fail the safe downloader.
# Do not retry them on every render until source policy or limits change.
KNOWN_UNUSABLE = {
 "dog-frisbee": "Source exceeds 125 MiB single-asset safety cap",
 "dog-frisbee-2": "Source exceeds 125 MiB single-asset safety cap",
 "dog-door-rush": "Source duration unsupported by downloader",
}
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=[]
 for src in SOURCES:
  row={**src,"publication_approved":False,"rights_verified":False,"actual_action_verified":False}
  path=OUT/(src["id"]+".mp4")
  if src["id"] in KNOWN_UNUSABLE:
   row["status"]="SKIPPED_KNOWN_UNUSABLE"
   row["error_detail"]=KNOWN_UNUSABLE[src["id"]]
   rows.append(row)
   print(row["id"],row["status"],flush=True)
   continue
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
