#!/usr/bin/env python3
"""Download/decode at most one small candidate per public provider for technical proof.
Rights remain unverified; this probe does not select footage for publishing.
"""
import argparse,hashlib,json,subprocess,urllib.request
from pathlib import Path
MAX_BYTES=18*1024*1024
def fetch_limited(url,dest):
 req=urllib.request.Request(url,headers={"User-Agent":"TOP5-Shorts-Research/1.0","Accept":"video/*,*/*"})
 with urllib.request.urlopen(req,timeout=45) as resp,open(dest,"wb") as out:
  size=0
  while True:
   chunk=resp.read(256*1024)
   if not chunk:break
   size+=len(chunk)
   if size>MAX_BYTES:raise ValueError("VIDEO_EXCEEDS_18MB_PROBE_CAP")
   out.write(chunk)
 return size
def inspect_video(path):
 info=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height,duration","-of","json",str(path)],capture_output=True,text=True,timeout=30,check=True)
 streams=json.loads(info.stdout).get("streams",[])
 if not streams or not streams[0].get("width"):raise ValueError("NO_VIDEO_STREAM")
 subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-map","0:v:0","-f","null","-"],check=True,timeout=120,capture_output=True)
 return streams[0]
def probe(candidates,out,fetch=fetch_limited,inspect=inspect_video):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);results=[];errors=[]
 for provider in ("wikimedia","internet_archive"):
  tested=0
  pool=[x for x in candidates if x.get("provider")==provider and x.get("license_gate")=="LICENSE_CANDIDATE_REVIEW_REQUIRED"]
  for row in pool[:5]:
   tested+=1;ext=Path(row.get("file_url","")).suffix.lower()
   if ext not in (".mp4",".webm",".ogv",".ogg",".m4v"):continue
   dest=out/(provider+"_probe"+ext)
   try:
    size=fetch(row["file_url"],dest);stream=inspect(dest)
    results.append({"provider":provider,"source_id":row.get("id"),"title":row.get("title"),"source_page":row.get("page_url"),"license_claim":row.get("license"),"bytes":size,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"video_stream":stream,"full_decode_pass":True,"rights_verified":False,"publication_approved":False,"file":dest.name})
    break
   except Exception as e:
    errors.append({"provider":provider,"id":row.get("id"),"reason":type(e).__name__})
    dest.unlink(missing_ok=True)
 return {"status":"TECHNICAL_PROBE_ONLY_NOT_LICENSE_CLEARED","results":results,"errors":errors,"provider_count_passed":len(results),"rights_verified":False,"publication_approved":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--discovery",default="output/top5_external_sources/DISCOVERY.json");p.add_argument("--output",default="output/top5_external_sources/probe");a=p.parse_args()
 data=json.loads(Path(a.discovery).read_text());report=probe(data.get("candidates",[]),a.output)
 (Path(a.output)/"PUBLIC_VIDEO_DOWNLOAD_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({"status":report["status"],"provider_count_passed":report["provider_count_passed"],"errors":report["errors"][:8]}))
if __name__=="__main__":main()
