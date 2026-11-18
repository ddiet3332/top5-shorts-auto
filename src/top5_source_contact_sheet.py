#!/usr/bin/env python3
"""Generate a reproducible 5x3 real-frame review contact sheet. No fake AI ratings."""
import argparse,io,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
FONT="/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
def frame(path,seconds):
 data=subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str(seconds),"-i",str(path),"-frames:v","1","-vf","scale=300:350:force_original_aspect_ratio=decrease","-f","image2pipe","-vcodec","mjpeg","-"],timeout=40)
 return Image.open(io.BytesIO(data)).convert("RGB")
def build(source_dir,out_dir):
 source_dir=Path(source_dir);out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
 qa=json.loads((source_dir/"SOURCE_DOWNLOAD_QA.json").read_text());sources=qa.get("sources",[])
 if len(sources)!=5:raise ValueError("Five source videos required")
 sheet=Image.new("RGB",(990,2070),"#101015");d=ImageDraw.Draw(sheet)
 font=ImageFont.truetype(FONT,24) if Path(FONT).exists() else ImageFont.load_default()
 frames=[]
 for i,s in enumerate(sources):
  path=source_dir/s["file"]
  if not path.is_file():raise FileNotFoundError(path)
  duration=float(s["duration_sec"])
  times=[round(duration*x,2) for x in (.15,.50,.85)]
  for j,t in enumerate(times):
   img=frame(path,t);x=15+j*325;y=15+i*410
   sheet.paste(img,(x+(300-img.width)//2,y+36+(350-img.height)//2))
   d.text((x,y),f"#{i+1} ID:{s['id']} @ {t:.2f}s",font=font,fill="white")
   frames.append({"source_id":s["id"],"time_sec":t,"source_file":s["file"]})
 path=out_dir/"TOP5_SOURCE_CONTACT_SHEET.jpg";sheet.save(path,quality=88)
 report={"status":"VISUAL_REVIEW_REQUIRED","contact_sheet":path.name,"frame_count":len(frames),"frames":frames,"editorial_score":None,"rankings_verified":False,"rights_verified":False,"publication_approved":False}
 (out_dir/"VISUAL_REVIEW_MANIFEST.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--output",default="output/top5_visual_review");a=p.parse_args()
 print(json.dumps(build(a.sources,a.output),ensure_ascii=False))
