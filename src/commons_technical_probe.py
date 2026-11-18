"""Probe real shortlisted Commons videos with bounded downloads and ffprobe.

Evidence is technical only. No source is marked rights verified or publishable.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

MAX_BYTES=125*1024*1024

def probe(inventory, output_dir, max_files=12):
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for source in inventory.get("candidates",[])[:max_files]:
        row={"id":source["id"],"title":source["title"],
             "source_url":source["source_url"],"license_raw":source["license_raw"],
             "rights_verified":False,"publication_approved":False}
        try:
            size=int(source["size_bytes"])
            if size<=0 or size>MAX_BYTES:
                raise ValueError("REJECT_SIZE")
            url=source["download_url"]
            if not url.startswith("https://upload.wikimedia.org/"):
                raise ValueError("REJECT_DOWNLOAD_HOST")
            target=out/(str(source["id"])+".webm")
            req=urllib.request.Request(url,headers={"User-Agent":"Top5ShortsAuto/0.1 (technical review)"})
            with urllib.request.urlopen(req,timeout=45) as response, target.open("wb") as handle:
                if response.geturl().split("/")[2]!="upload.wikimedia.org":
                    raise ValueError("REJECT_REDIRECT_HOST")
                total=0
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:
                        break
                    total+=len(chunk)
                    if total>MAX_BYTES:
                        raise ValueError("REJECT_SIZE")
                    handle.write(chunk)
            result=subprocess.run(["ffprobe","-v","error","-show_entries",
                "format=duration,size:stream=codec_type,width,height",
                "-of","json",str(target)],capture_output=True,text=True,timeout=35,check=True)
            meta=json.loads(result.stdout)
            streams=[x for x in meta.get("streams",[]) if x.get("codec_type")=="video"]
            if not streams:
                raise ValueError("REJECT_NO_VIDEO")
            video=streams[0]
            duration=float(meta["format"]["duration"])
            width=int(video["width"])
            height=int(video["height"])
            row.update({"duration_sec":duration,"width":width,"height":height,
                        "downloaded_bytes":total,"technical_pass":5<=duration<=60 and min(width,height)>=720,
                        "local_path":str(target)})
            row["code"]="PASS_TECHNICAL_ONLY" if row["technical_pass"] else "REJECT_TECHNICAL"
        except (OSError,ValueError,KeyError,subprocess.SubprocessError,TimeoutError) as exc:
            row.update({"technical_pass":False,"code":"REJECT_PROBE_ERROR",
                        "error":type(exc).__name__,"error_detail":str(exc)[:240]})
        results.append(row)
    return {"status":"TECHNICAL_PROBE_NOT_RIGHTS_APPROVAL",
            "probed":len(results),"technical_pass_count":sum(x["technical_pass"] for x in results),
            "results":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--max-files",type=int,default=12)
    a=p.parse_args()
    report=probe(json.loads(Path(a.input).read_text(encoding="utf-8")),
                 a.output_dir,a.max_files)
    (Path(a.output_dir)/"technical_probe.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"probed":report["probed"],"technical_pass_count":report["technical_pass_count"]}))
if __name__=="__main__":
    main()
