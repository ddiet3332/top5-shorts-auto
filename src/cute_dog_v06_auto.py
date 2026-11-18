#!/usr/bin/env python3
"""Render the approved V06 visual template from a NEW five-source Pixabay preview."""
import json, subprocess, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE=Path("output/dog_pixabay_preview")
SOURCE=BASE/"DOG_TOP5_SOURCE_REVIEW_ONLY_25s.mp4"
OUT=BASE/"CUTE_DOG_TOP5_V06_AUTO_25s.mp4"
NAMES=["표정 부자","얌전한 아기","옆모습 심쿵","들판 요정","꿀잠 천사"]
CAPTIONS=["이 표정은 반칙이지!","가만히 있어도 심쿵!","옆모습까지 귀여워","들판에서 만난 천사","잠든 모습도 사랑스러워"]
FONT="/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

def main():
    if not SOURCE.is_file(): raise SystemExit("No real source preview; blocked")
    if not Path(FONT).is_file(): raise SystemExit("Missing Korean font; blocked")
    audit=json.loads((BASE/"DOG_PIXABAY_RENDER_AUDIT.json").read_text())
    if audit.get("usable_previews")!=5: raise SystemExit("Not five real clips; blocked")
    f=lambda n:ImageFont.truetype(FONT,n)
    for i in range(5):
        im=Image.new("RGBA",(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im)
        d.rectangle((0,0,1080,320),fill=(0,0,0,255))
        d.text((540,157),"귀여운 강아지 순간",font=f(49),fill="#FFDB21",anchor="mm")
        d.text((540,238),"TOP5",font=f(70),fill="white",anchor="mm")
        d.rounded_rectangle((0,335,360,1230),radius=12,fill=(0,0,0,205))
        for rank in range(5,5-i-1,-1):
            y=425+(rank-1)*160
            color="#FFDB21" if rank==5-i else "white"
            d.text((17,y),f"{rank}위",font=f(48),fill=color,stroke_width=1,stroke_fill="black")
            d.text((118,y+7),NAMES[5-rank],font=f(29),fill=color,stroke_width=1,stroke_fill="black")
        cy=1344
        d.rounded_rectangle((95,cy-67,985,cy+67),radius=16,fill=(0,0,0,210))
        d.text((540,cy),CAPTIONS[i],font=f(51),fill="white",anchor="mm",stroke_width=2,stroke_fill="black")
        im.save(BASE/f"v06_overlay_{i}.png")
    inputs=["-i",str(SOURCE)]
    for i in range(5): inputs+=["-loop","1","-i",str(BASE/f"v06_overlay_{i}.png")]
    flt="[0:v]format=yuv420p[v0];"
    for i in range(5):
        flt+=f"[v{i}][{i+1}:v]overlay=0:0:enable='gte(t,{i*5})*lt(t,{(i+1)*5})':shortest=1[v{i+1}];"
    flt+="[v5]format=yuv420p[vout]"
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",*inputs,"-filter_complex",flt,"-map","[vout]","-map","0:a?","-t","25","-r","24","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",str(OUT)],check=True,timeout=300)
    subprocess.run(["ffmpeg","-v","error","-i",str(OUT),"-f","null","-"],check=True,timeout=120)
    report={"status":"V06_RENDERED_REVIEW_ONLY","template":"V06_BOTTOM_UP_RANK","topic":"cute puppy","new_source_query":audit.get("query"),"real_clips":5,"mp4":OUT.name,"sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),"rights_verified":False,"publication_approved":False}
    (BASE/"V06_AUTO_AUDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("V06 MP4:",OUT,"sha256:",report["sha256"])
if __name__=="__main__":main()
