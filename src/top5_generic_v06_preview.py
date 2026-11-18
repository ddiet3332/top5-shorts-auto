#!/usr/bin/env python3
"""Generic V06 TOP5 REVIEW preview from five real decoded source files.
No fabricated editorial captions or publication approval.
"""
import argparse,hashlib,json,subprocess,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
FONT="/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
def run(cmd,timeout=180):
 subprocess.run(cmd,check=True,timeout=timeout,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
TAG_KO={"butterfly":"나비","swallowtail":"호랑나비","macro":"접사","close up":"근접 촬영","flower":"꽃","wildflower":"들꽃","blossom":"꽃","bloom":"개화","nature":"자연","grass":"풀밭","field":"들판","summer":"여름","insect":"곤충","insects":"곤충","plant":"식물","plants":"식물","beautiful":"아름다운 순간"}
def source_label(source):
 """Use provider metadata only, never pretend to have visually recognized an action."""
 raw=[x.strip().lower() for x in str(source.get("tags","")).split(",")]
 labels=[]
 for tag in raw:
  val=TAG_KO.get(tag)
  if val and val not in labels and val not in ("나비","곤충"):labels.append(val)
 return " · ".join(labels[:2]) or "나비 영상"
def render(plan_path,source_dir,out_dir):
 plan=json.loads(Path(plan_path).read_text());audit=json.loads((Path(source_dir)/"SOURCE_DOWNLOAD_QA.json").read_text())
 sources=audit.get("sources",[])
 if len(sources)!=5 or audit.get("downloaded_valid_sources")!=5:raise ValueError("Five decoded sources required")
 if not Path(FONT).exists():raise ValueError("Missing Nanum font")
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
 font=lambda n:ImageFont.truetype(FONT,n)
 title=str(plan["selected"]["topic"]).replace(" TOP5","")[:20]
 labels=["장면 검수 필요"]*5
 # Provider tags are search metadata, not verified descriptions of the visible scene.
 parts=[]
 for i,source in enumerate(sources):
  path=Path(source_dir)/source["file"]
  if not path.is_file():raise ValueError("Missing source file")
  part=out/("normalized_%d.mp4"%i)
  vf="[0:v]split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[blur];[fg]scale=1080:1600:force_original_aspect_ratio=decrease[subject];[blur][subject]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=24,format=yuv420p[v]"
  run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(path),"-t","5","-filter_complex",vf,"-map","[v]","-an","-c:v","libx264","-preset","veryfast","-crf","25","-pix_fmt","yuv420p",str(part)])
  parts.append(part)
 concat=out/"concat.txt";concat.write_text("".join("file '"+p.name+"'\n" for p in parts))
 base=out/"base.mp4"
 run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),"-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","25","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","96k",str(base)])
 for i in range(5):
  im=Image.new("RGBA",(1080,1920),(0,0,0,0));d=ImageDraw.Draw(im)
  d.rectangle((0,0,1080,320),fill=(0,0,0,255))
  d.text((540,157),title,font=font(46),fill="#FFDB21",anchor="mm")
  d.text((540,238),"TOP5",font=font(70),fill="white",anchor="mm")
  d.rounded_rectangle((0,335,360,1230),radius=12,fill=(0,0,0,205))
  for rank in range(5,5-i-1,-1):
   y=425+(rank-1)*160;color="#FFDB21" if rank==5-i else "white"
   d.text((20,y),f"{rank}위",font=font(48),fill=color,stroke_width=1,stroke_fill="black")
   d.text((115,y+10),labels[5-rank],font=font(25),fill=color)
  d.rounded_rectangle((95,1277,985,1411),radius=16,fill=(0,0,0,210))
  d.text((540,1344),f"{5-i}위 · 장면 검수 필요",font=font(43),fill="white",anchor="mm")
  d.text((540,1850),"장면·순위·권리 검수 전",font=font(29),fill="white",anchor="mm",stroke_width=2,stroke_fill="black")
  im.save(out/("overlay_%d.png"%i))
 inputs=["-i",str(base)]
 for i in range(5):inputs+=["-loop","1","-i",str(out/("overlay_%d.png"%i))]
 filt="[0:v]format=yuv420p[v0];"
 for i in range(5):filt+=f"[v{i}][{i+1}:v]overlay=0:0:enable='gte(t,{i*5})*lt(t,{(i+1)*5})':shortest=1[v{i+1}];"
 filt+="[v5]format=yuv420p[vout]"
 final=out/"TOP5_V06_GENERIC_REVIEW_25s.mp4"
 run(["ffmpeg","-hide_banner","-loglevel","error","-y",*inputs,"-filter_complex",filt,"-map","[vout]","-map","0:a:0","-t","25","-r","24","-c:v","libx264","-preset","veryfast","-crf","24","-pix_fmt","yuv420p","-c:a","aac","-b:a","96k",str(final)],timeout=360)
 run(["ffmpeg","-v","error","-xerror","-i",str(final),"-f","null","-"],timeout=150)
 result={"status":"GENERIC_V06_REVIEW_RENDERED_NOT_APPROVED","topic":plan["selected"]["topic"],"file":final.name,"sha256":hashlib.sha256(final.read_bytes()).hexdigest(),"editorial_score":None,"rights_verified":False,"publication_approved":False,"rankings_verified":False,"source_count":5,"caption_method":"safe_review_placeholder_not_visual_analysis","captions":labels}
 (out/"GENERIC_V06_QA.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--output",default="output/top5_v06_review");a=p.parse_args()
 print(json.dumps(render(a.plan,a.sources,a.output),ensure_ascii=False))
if __name__=="__main__":main()
