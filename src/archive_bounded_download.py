"""Bounded, fail-closed Internet Archive original video downloader.

No rights or publication approval is inferred from an Archive metadata license.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES=125*1024*1024
def fetch_file(row, destination, opener=urllib.request.urlopen):
    url=row["download_url"]
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname!="archive.org" or not parsed.path.startswith("/download/"):
        return {"status":"REJECT_UNTRUSTED_URL"}
    declared=int(row.get("size") or 0)
    if declared<=0 or declared>MAX_BYTES:
        return {"status":"REJECT_SIZE"}
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(url,headers={"User-Agent":"Top5ShortsAuto/0.1 (GitHub ddiet3332/top5-shorts-auto)"})
    size=0
    digest=hashlib.sha256()
    try:
        with opener(req,timeout=40) as response, destination.open("wb") as target:
            final=urllib.parse.urlsplit(response.geturl())
            if final.scheme!="https" or not (final.hostname=="archive.org" or final.hostname.endswith(".archive.org")):
                raise ValueError("Unexpected redirect host")
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                size+=len(chunk)
                if size>MAX_BYTES or size>declared+1024:
                    raise ValueError("Source exceeded declared size")
                digest.update(chunk)
                target.write(chunk)
        if size==0: raise ValueError("Empty source")
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height",
             "-of","json",str(destination)],capture_output=True,text=True,timeout=25)
        if probe.returncode!=0: raise ValueError("ffprobe rejected downloaded file")
        metadata=json.loads(probe.stdout)
        streams=[s for s in metadata.get("streams",[]) if s.get("codec_type")=="video"]
        duration=float(metadata.get("format",{}).get("duration") or 0)
        if not streams or not 5<=duration<=60 or min(int(s.get("width") or 0),int(s.get("height") or 0))<720:
            raise ValueError("Media fails duration/resolution gate")
        return {"status":"TECHNICAL_PASS_PENDING_SEMANTIC_AND_RIGHTS","local_path":str(destination),
                "sha256":digest.hexdigest(),"downloaded_bytes":size,"duration_sec":duration,
                "width":streams[0].get("width"),"height":streams[0].get("height"),
                "technical_pass":True}
    except (OSError,ValueError,TimeoutError,subprocess.SubprocessError) as exc:
        destination.unlink(missing_ok=True)
        return {"status":"DOWNLOAD_OR_TECHNICAL_FAILURE","error":type(exc).__name__,"detail":str(exc)[:240],
                "technical_pass":False}

def run(preflight, output_dir, max_files=6):
    root=Path(output_dir)
    results=[]
    for item in preflight.get("results",[]):
        if item.get("status")!="PREFLIGHT_METADATA_ONLY_PENDING_DOWNLOAD_AND_RIGHTS": continue
        for f in item.get("files",[])[:1]:
            if len(results)>=max_files: break
            extension=Path(f["name"]).suffix.lower()
            if extension not in (".mp4",".webm",".mov",".m4v",".ogv"): continue
            result=fetch_file(f,root/"media"/(hashlib.sha256(item["id"].encode()).hexdigest()[:16]+extension))
            result.update({"id":item["id"],"title":item.get("title"),"creator":item.get("creator"),
                "license_url":item.get("license_url"),"source_url":"https://archive.org/details/"+urllib.parse.quote(item["id"]),
                "rights_verified":False,"publication_approved":False})
            results.append(result)
        if len(results)>=max_files: break
    return {"status":"TECHNICAL_EVIDENCE_ONLY_NOT_RIGHTS_APPROVAL","attempted":len(results),
            "technical_pass_count":sum(x["technical_pass"] for x in results),"results":results}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--max-files",type=int,default=6)
    a=p.parse_args()
    root=Path(a.output_dir)
    root.mkdir(parents=True,exist_ok=True)
    result=run(json.loads(Path(a.input).read_text(encoding="utf-8")),root,max(0,min(a.max_files,10)))
    (root/"technical_probe.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"attempted":result["attempted"],"technical_pass_count":result["technical_pass_count"]}))
if __name__=="__main__": main()
