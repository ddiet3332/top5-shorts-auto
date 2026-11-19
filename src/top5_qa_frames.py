#!/usr/bin/env python3
"""Extract deterministic editorial review frames; never invent visual scores."""
import argparse
import json
import subprocess
from pathlib import Path

def extract(video, outdir, count=15):
    video=Path(video)
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-of","json",str(video)],text=True))
    duration=float(probe["format"]["duration"])
    frames=[]
    for i in range(count):
        t=duration*(i+0.5)/count
        target=outdir/f"frame_{i+1:02d}.jpg"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-ss",f"{t:.3f}","-i",str(video),"-frames:v","1","-vf","scale=360:-2","-y",str(target)],check=True)
        frames.append({"time_seconds":round(t,3),"path":str(target),"file":target.name})
    report={"video":video.name,"duration_seconds":duration,"frame_count":len(frames),
            "frames":frames,"visual_editorial_review_completed":False,
            "editorial_score_100":None,"publication_approved":False}
    (outdir/"FRAME_REVIEW_MANIFEST.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--count",type=int,default=15)
    a=p.parse_args()
    if not 5<=a.count<=30:
        p.error("--count must be 5..30")
    print(json.dumps(extract(a.video,a.output,a.count),ensure_ascii=False))
