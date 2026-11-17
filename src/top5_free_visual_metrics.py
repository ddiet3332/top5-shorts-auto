#!/usr/bin/env python3
"""Free, deterministic visual proxy metrics; never claim semantic editorial scores."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

def analyze(manifest, output):
    data=json.loads(Path(manifest).read_text(encoding="utf-8"))
    entries=data.get("frames",[])
    if len(entries)<5:
        raise ValueError("Insufficient review frames")
    frames=[]
    for item in entries:
        p=Path(item["path"])
        if not p.exists():
            raise FileNotFoundError(p)
        with Image.open(p) as im:
            frames.append(im.convert("L").resize((90,160)).copy())
    changes=[]
    for a,b in zip(frames,frames[1:]):
        diff=ImageChops.difference(a,b)
        changes.append(round(ImageStat.Stat(diff).mean[0]/255,5))
    very_similar=sum(v<0.015 for v in changes)
    motion_variety=round(sum(v>=0.04 for v in changes)/len(changes),3)
    result={"schema_version":1,"cost_usd":0,"sampled_frame_count":len(frames),
            "adjacent_frame_mean_absolute_difference":changes,
            "very_similar_adjacent_pairs":very_similar,
            "visual_change_pair_ratio":motion_variety,
            "possible_static_or_repetitive_visuals":very_similar>=len(changes)//2,
            "editorial_score_100":None,"fun_reversal_score":None,
            "rights_cleared":False,"publication_approved":False,
            "limitation":"Frame changes are not motion understanding, humor, narrative, or license verification."}
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    print(json.dumps(analyze(a.manifest,a.output),ensure_ascii=False))
