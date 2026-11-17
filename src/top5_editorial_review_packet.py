#!/usr/bin/env python3
"""Prepare evidence for seven-category TOP5 editorial review without fabricating scores."""
import argparse
import hashlib
import json
from pathlib import Path

LIMITS={"hook":20,"fun_reversal":25,"ranking":15,"flow":15,"original_captions":10,"sound":10,"rights_monetization":5}
PROMPTS={
 "hook":"Does the first 0-2 seconds show a concrete surprising action, not just a title?",
 "fun_reversal":"Are there five distinct funny, surprising or emotional payoffs? Are claims supported by actual actions?",
 "ranking":"Do ranks 5 through 1 match the five footage segments and have defensible escalation?",
 "flow":"Are transitions, source continuity, timing and visual diversity coherent?",
 "original_captions":"Are Korean captions readable, accurate, original, and not obscuring action?",
 "sound":"Is audio synchronized, clear, free of clipping, and meaningfully supporting the story?",
 "rights_monetization":"Are all five underlying clips independently rights-cleared and the edit transformative under platform rules?"
}
def build(video,manifest,frames):
    video=Path(video)
    m=json.loads(Path(manifest).read_text(encoding="utf-8"))
    f=json.loads(Path(frames).read_text(encoding="utf-8"))
    if not video.is_file():
        raise FileNotFoundError(video)
    h=hashlib.sha256()
    with video.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    clips=m.get("clips",[])
    if len(clips)!=5 or len(f.get("frames",[]))!=15:
        raise ValueError("Expected five clips and fifteen review frames")
    return {
      "schema_version":1,"video_sha256":h.hexdigest(),
      "review_required":True,"automatic_editorial_score":None,
      "seven_category_limits":LIMITS,"review_questions":PROMPTS,
      "clips":[{"rank":c.get("rank"),"source_page":c.get("source_page"),
                "editorial_verified":False,"rights_verified":False} for c in clips],
      "sampled_frames":f["frames"],
      "missing_evidence":["Full moving-video review","Independent license/creator rights for five sources",
                          "Human or explicitly authorized AI seven-category evaluation"],
      "reviewer":None,"reviewed_at":None,"editorial_scores":None,
      "rights_monetization_approved":False,"publication_approved":False,
      "warning":"Fifteen still frames alone cannot verify motion, humor, audio or legal rights."
    }
def main():
    p=argparse.ArgumentParser()
    for key in ("video","manifest","frames","output"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    result=build(a.video,a.manifest,a.frames)
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Editorial review packet created; creative score withheld until reviewed.")
if __name__=="__main__":
    main()
