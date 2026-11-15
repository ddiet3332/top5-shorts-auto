#!/usr/bin/env python3
"""V26 caption-only editorial rework of the actual 5-source V25 master.

All source footage originates from Pexels/Commons licenses recorded in the
source catalog. No source audio is restored; the existing self-synthesized AAC
track is copied byte-for-byte. Rendering is a technical step, NOT a grant of
original uploader's rights, third-party rights or YT monetization approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HEADER="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Label,NanumSquare,43,&H0052D1F7,&H00FFFFFF,&H00201C16,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,20,20,20,1
Style: Head,NanumSquare,49,&H00FFFFFF,&H00FFFFFF,&H00201C16,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,20,20,20,1
Style: Detail,NanumSquare,34,&H00D9D2C9,&H00D9D2C9,&H00201C16,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,20,20,20,1
Style: Steps,NanumSquare,31,&H005FDCF5,&H005FDCF5,&H00201C16,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,20,20,20,1
Style: Footer,NanumSquare,25,&H00C4BBC1,&H00C4BBC1,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,20,20,20,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

def validate_storyboard(data):
    if not isinstance(data,dict) or data.get("schema_version")!=1:
        raise ValueError("Unsupported V26 storyboard schema")
    if data.get("no_tts") is not True or data.get("no_voiceover") is not True:
        raise ValueError("V26 can never request voiceover")
    if data.get("use_only_original_synthesized_sfx") is not True:
        raise ValueError("No source audio or outside music clearance")
    if data.get("auto_publish") is not False:
        raise ValueError("Never automatically grant YouTube publication rights")
    windows=data.get("windows")
    if not isinstance(windows,list) or len(windows)!=12:
        raise ValueError("Exactly 12 observed storyboard beats required")
    t=0.0
    for w in windows:
        if not isinstance(w,dict) or abs(float(w.get("start_sec",-1))-t)>0.00001:
            raise ValueError("No subtitle gaps or crossfade overlaps")
        t=float(w["end_sec"])
        if t<=float(w["start_sec"]) or t>30.0:
            raise ValueError("Beat times out of allowed 30 seconds")
        if any(not isinstance(w.get(k),str) or not w[k].strip() for k in ("label","phase","headline","detail")):
            raise ValueError("All action commentary requires original written text")
        if not isinstance(w.get("stages"),list) or len(w["stages"])!=3:
            raise ValueError("Each beat must have exactly 3 truthful observation steps")
    if abs(t-30.0)>0.00001:return False
    return True

def stamp(sec):
    cs=round(sec*100)
    h,cs=divmod(cs,360000);minute,cs=divmod(cs,6000);second,cs=divmod(cs,100)
    return f"{h}:{minute:02}:{second:02}.{cs:02}"

def escape(s):
    return s.replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}").replace("\n",r"\N")

def make_ass(data):
    if not validate_storyboard(data):
        raise ValueError("Storyboard not 30sec")
    lines=[]
    def ev(a,b,style,x,y,txt):
        lines.append(f"Dialogue: 5,{stamp(a)},{stamp(b)},{style},,0,0,0,,"
                     "{\\an7\\pos("+f"{x},{y}"+")}" +escape(txt))
    for w in data["windows"]:
        a=float(w["start_sec"]);b=float(w["end_sec"])
        ev(a,b,"Label",81,1519,w["label"]+"  /  "+w["phase"])
        ev(a,b,"Head",81,1609,w["headline"])
        ev(a,b,"Detail",81,1674,w["detail"])
        ev(a,b,"Steps",81,1735,"   →   ".join(w["stages"]))
    ev(0,30,"Footer",58,1835,"TOP5  ·  독창적 상황 해설 · 자체 제작 효과음")
    ev(0,30,"Footer",58,1875,"무료 라이선스 원본 및 저작자 표기: 영상 설명란")
    return HEADER+"\n".join(lines)+"\n"

def probe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams",
                      "-of","json",str(path)],text=True,capture_output=True,check=True,timeout=30)
    return json.loads(r.stdout)

def audio_hash(path):
    p=subprocess.Popen(["ffmpeg","-v","error","-i",str(path),"-map","0:a:0",
                        "-c:a","copy","-f","data","-"],stdout=subprocess.PIPE)
    h=hashlib.sha256()
    for b in iter(lambda:p.stdout.read(64*1024),b""):
        h.update(b)
    if p.wait()!=0:
        raise ValueError("Could not hash original self-produced soundtrack")
    return h.hexdigest()

def build(base,output,board,working):
    base=Path(base);output=Path(output);working=Path(working)
    if not base.is_file():raise FileNotFoundError(base)
    output.parent.mkdir(parents=True,exist_ok=True)
    working.mkdir(parents=True,exist_ok=True)
    story=json.loads(Path(board).read_text(encoding="utf-8"))
    a=working/"V26_ORIGINAL_EDITORIAL.ass"
    a.write_text(make_ass(story),encoding="utf-8")
    vf=("drawbox=x=0:y=1490:w=1080:h=430:color=black:t=fill,"
        "drawbox=x=54:y=1505:w=972:h=275:color=0x111926:t=fill,"
        "drawbox=x=54:y=1505:w=7:h=275:color=0xF5D152:t=fill,"
        f"ass={a}")
    subprocess.run(["ffmpeg","-hide_banner","-v","error","-y",
                    "-i",str(base),"-vf",vf,"-map","0:v:0","-map","0:a:0",
                    "-t","30","-r","24","-c:v","libx264","-preset","ultrafast",
                    "-crf","19","-pix_fmt","yuv420p","-c:a","copy",
                    "-movflags","+faststart",str(output)],check=True,timeout=350)
    info=probe(output)
    videos=[s for s in info["streams"] if s.get("codec_type")=="video"]
    audios=[s for s in info["streams"] if s.get("codec_type")=="audio"]
    if (len(videos)!=1 or len(audios)!=1 or videos[0].get("codec_name")!="h264"
        or audios[0].get("codec_name")!="aac" or videos[0].get("width")!=1080
        or videos[0].get("height")!=1920 or videos[0].get("r_frame_rate")!="24/1"
        or abs(float(info["format"]["duration"])-30)>0.05):
        raise ValueError("Complete 30s 1080x1920 H264/AAC video required")
    if audio_hash(base)!=audio_hash(output):
        raise ValueError("Original synthetic audio changed or external soundtrack entered")
    subprocess.run(["ffmpeg","-hide_banner","-v","error","-xerror",
                    "-i",str(output),"-map","0:v:0","-map","0:a:0",
                    "-f","null","-"],check=True,timeout=230)
    report={
      "status":"V26_REAL_30S_AV_DECODE_PASSED_NO_MONETIZATION_APPROVAL",
      "video_file":output.name,
      "duration":float(info["format"]["duration"]),
      "resolution":"1080x1920","fps":24,"video":"H264","audio":"AAC",
      "source_originals":5,
      "soundtrack_same_original_synth_aac":True,
      "no_tts":True,"no_narration":True,
      "new_visual_editorial_beats":len(story["windows"]),
      "underlying_provider_licenses":"Pexels 3; Commons CC0 1; CC BY 3.0 1",
      "final_creator_and_third_party_rights_independently_proven":False,
      "YouTube_reused_content_monetization_guaranteed":False,
      "approved_for_publication_automatically":False
    }
    (working/"V26_FREE_TECHNICAL_QA.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V26 free source 30s editorial master decoded, 12 accurate beats, original synthesized AAC unchanged",flush=True)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="output/TOP5_V25_SITUATION_CAPTIONS_REVIEW_ONLY_1080x1920.mp4")
    p.add_argument("--output",default="output/TOP5_V26_FREE_EDITORIAL_UPLOAD_CANDIDATE.mp4")
    p.add_argument("--board",default="sample/v26-free-editorial-storyboard.json")
    p.add_argument("--scratch",default="output/v26_free_editorial_work")
    args=p.parse_args()
    build(args.input,args.output,args.board,args.scratch)

if __name__=="__main__":
    main()
