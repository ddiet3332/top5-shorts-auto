#!/usr/bin/env python3
"""Generic V06 TOP5 REVIEW preview from five real decoded source files.
No fabricated editorial captions or publication approval.
"""
import argparse,json,os,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
FONT=os.environ.get("TOP5_KOREAN_FONT", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
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
def load_reviewed_captions(review_path,sources):
 if not review_path:return None
 review=json.loads(Path(review_path).read_text(encoding="utf-8"))
 if review.get("verified_by_human") is not True:raise ValueError("Caption review must be explicitly human verified")
 entries=review.get("entries")
 if not isinstance(entries,list) or len(entries)!=5:raise ValueError("Exactly five reviewed entries required")
 result=[]
 for i,e in enumerate(entries):
  if str(e.get("source_id"))!=str(sources[i].get("id")):raise ValueError("Caption/source order mismatch at "+str(i))
  name=e.get("rank_name");caption=e.get("caption")
  if not isinstance(name,str) or not 2<=len(name.strip())<=16:raise ValueError("Invalid rank name")
  if not isinstance(caption,str) or not 3<=len(caption.strip())<=38:raise ValueError("Invalid caption")
  result.append((name.strip(),caption.strip()))
 return result


class LayoutError(ValueError):
    pass


def fit_text(draw, text, center, bounds, size, color, stroke=0):
    for font_size in range(size, 23, -2):
        font = ImageFont.truetype(FONT, font_size)
        box = draw.textbbox(center, text, font=font, anchor="mm", stroke_width=stroke)
        if box[0] >= bounds[0] and box[1] >= bounds[1] and box[2] <= bounds[2] and box[3] <= bounds[3]:
            draw.text(center, text, font=font, fill=color, anchor="mm",
                      stroke_width=stroke, stroke_fill="black")
            return
    raise LayoutError("자막 안전 영역에 맞지 않습니다")


def overlay(path, title, rank, caption):
    image = Image.new("RGBA", (1080, 1920))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1079, 339), fill="black")
    fit_text(draw, title, (520, 155), (65, 70, 975, 215), 76, "#ffdb19")
    fit_text(draw, "TOP5", (520, 267), (65, 216, 975, 327), 76, "white")
    for number in range(1, 6):
        fit_text(draw, f"{number}위", (108, 520 + (number - 1) * 128),
                 (24, 408, 197, 1110), 62 if number == rank else 49,
                 "#ffdb19" if number == rank else "white", stroke=5)
    fit_text(draw, caption, (500, 1480), (72, 1370, 928, 1575), 74, "white", stroke=7)
    image.save(path)


def render(plan_path, source_dir, out_dir, review_path=None, qa_path=None, rights_path=None):
    from top5_production_review import produce
    return produce(Path(plan_path), Path(source_dir), Path(out_dir), review_path, qa_path, rights_path)

def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",default="output/topic_plan.json");p.add_argument("--sources",default="output/top5_source_qa");p.add_argument("--output",default="output/top5_v06_review");p.add_argument("--reviewed-captions");p.add_argument("--editorial-review");p.add_argument("--rights-review");a=p.parse_args()
 print(json.dumps(render(a.plan,a.sources,a.output,a.reviewed_captions,a.editorial_review,a.rights_review),ensure_ascii=False))
if __name__=="__main__":main()
