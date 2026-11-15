#!/usr/bin/env python3
"""V15 CC0 4.3-second cat action short-film audition.

Use only an exact Wikimedia Commons title and current license metadata.
A gentle 1.16x time stretch makes a ~5sec review preview with no repeated frames.
Does NOT confer publication rights or judge comedy.
"""
import json
from pathlib import Path
import subprocess
from top5 import fetch_json,extract_candidates,download_video,probe_duration

TITLE="File:Kitten jumping on bamboo mat.webm"

def run(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    doc=fetch_json({"action":"query","format":"json","formatversion":"2",
                    "titles":TITLE,"prop":"imageinfo","iiprop":"url|size|mime|extmetadata"})
    result=[x for x in extract_candidates(doc) if x['title']==TITLE and "CC0" in x['license']]
    if len(result)!=1:
        raise RuntimeError("Exact Wikimedia CC0 short video metadata was not confirmed")
    c=result[0]
    source=out/"V15_SHORT_ORIGINAL.webm"
    download_video(c,source)
    duration=probe_duration(source)
    if not 4.0<=duration<=4.9:
        raise RuntimeError("Source changed, short-video retiming not approved")
    # Keep the whole source, simply render slightly slower to cover a 5s rank segment.
    speed=5.12/duration
    outvid=out/"V15_SHORT_PREVIEW.mp4"
    vf=(f"setpts={speed:.6f}*(PTS-STARTPTS),"
        "scale=540:960:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=540:960:(ow-iw)/2:(oh-ih)/2:color=black,"
        "fps=24,setsar=1,format=yuv420p")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(source),
        "-an","-vf",vf,"-t","5.12","-c:v","libx264","-preset","fast",
        "-crf","25","-movflags","+faststart",str(outvid)],
        check=True,timeout=80)
    result={"title":TITLE,"source_page":c["source_page"],
            "creator":c["author"],"license":c["license"],
            "license_url":c["license_url"],"duration_original":duration,
            "retiming_factor":speed,"original_audio_approved":False,
            "actual_comedic_payoff_verified":False,"approved_for_publication":False}
    (out/"V15_SHORT_AUDIT.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    source.unlink()
    print("[V15 short] CC0 verified, 4.3sec original slowed into 5sec editorial preview",flush=True)

if __name__=="__main__":
    run("output")
