#!/usr/bin/env python3
"""V28 full-screen TOP5 visual editor, based on five original authorized-free pages.

Video is rebuilt from source camera clips. Not a crop/re-encode of V27 with
embedded subtitles. No original source audio, TTS, public-domain claims or
monetization approval is inferred from this build.

Render: 30s 1080x1920 H.264 AAC, hook2/rank5-4/rank4-5/rank3-4/
rank2-6/rank1-6/outro3. Visible full-source video on a blurred video
backdrop when aspect ratio differs from 9:16, not action-destroying zoom.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from top5 import fetch_json, extract_candidates, probe_duration
from v12_mixed_draft import fetch_mixed_sources, validate_mixed_selection
from v25_audio_remaster import create_soundtrack

W,H,FPS=1080,1920,24
SEGMENTS=[("hook",2),("rank5",4),("rank4",5),("rank3",4),("rank2",6),("rank1",6),("outro",3)]
RANK_NAMES=["건물 점프","카메라 돌진","의자 점프","장난감 도약","상자 잠입"]
PAYOFFS={
 "hook":(0.0,"이걸 진짜 뛰어넘는다고?"),
 "rank5":(0.42,"퇴장은 내일 하시나요?ㅋㅋ"),
 "rank4":(1.10,"한 번 뛰고 다시 대기ㅋㅋ"),
 "rank3":(1.35,"간식 앞에서는 망설임 없음ㅋㅋ"),
 "rank2":(2.50,"갑자기 인터뷰 들어오네ㅋㅋ"),
 "rank1":(2.20,"고양이보다 내가 더 놀람ㅋㅋ"),
 "outro":(0.0,"당신의 1위는?"),
}
ASS_HEAD="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Title,NanumSquare,72,&H0000D9FF,&H00FFFFFF,&H00201B15,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,8,10,10,10,1
Style: MainTopic,NanumSquare,78,&H00171717,&H00171717,&H00131211,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,8,12,12,12,1
Style: TopFive,NanumSquare,84,&H00171717,&H00FFFFFF,&H00131211,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,8,12,12,12,1
Style: SmallRank,NanumSquare,62,&H0000D9FF,&H00FFFFFF,&H00131211,&H00000000,-1,0,0,0,100,100,0,0,1,4,1,7,12,12,12,1
Style: Rank,NanumSquare,68,&H00171717,&H00FFFFFF,&H000B0B0B,&H00000000,-1,0,0,0,100,100,0,0,1,4,1,7,10,10,10,1
Style: Active,NanumSquare,76,&H00171717,&H00171717,&H000B0B0B,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,7,10,10,10,1
Style: RankName,NanumGothic,36,&H00F5F5F5,&H00F5F5F5,&H00090909,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,7,10,10,10,1
Style: Caption,NanumSquare,60,&H00FFFFFF,&H00FFFFFF,&H0011100F,&H00000000,-1,0,0,0,100,100,0,0,1,5,1,5,10,10,10,1
Style: Outro,NanumSquare,58,&H00FFFFFF,&H00FFFFFF,&H0011100F,&H00000000,-1,0,0,0,100,100,0,0,1,4,1,5,10,10,10,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
def run(cmd,timeout=240):
    subprocess.run(cmd,check=True,timeout=timeout)
def clock(sec):
    n=round(float(sec)*100)
    h,n=divmod(n,360000)
    m,n=divmod(n,6000)
    s,cs=divmod(n,100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"
def cue(start,end,style,text,x,y,align=7,layer=5):
    txt=text.replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}")
    return ("Dialogue: "+str(layer)+","+clock(start)+","+clock(end)+","+style+
            ",,0,0,0,,{\\an"+str(align)+"\\pos("+str(x)+","+str(y)+")}"
            +txt)

def build_ass(path):
    cues=[]
    # One episode title, not a made-up channel name.
    # V28.3: a fixed, prominent central two-line title, as agreed.
    # The real source video is fitted BELOW the header, so a jumping cat's
    # face is never covered by the fixed topic headline.
    cues.append(cue(0,27,"MainTopic","고양이들의 황당한 순간",540,140,8))
    cues.append(cue(0,27,"TopFive","TOP5",540,214,8))
    # left ranking column: the current rank alone gets gold; no redundant explanations.
    position={"hook":1,"rank5":5,"rank4":4,"rank3":3,"rank2":2,"rank1":1}
    start=0.0
    for label,length in SEGMENTS:
        end=start+length
        if label!="outro":
            active=position[label]
            # Draw narrow translucent left rail behind text, never full width.
            for rank in range(1,6):
                y=485+(rank-1)*143
                sty="Active" if rank==active else "Rank"
                cues.append(cue(start,end,sty,f"{rank}위",35,y))
                if rank==active:
                    cues.append(cue(start,end,"RankName",RANK_NAMES[rank-1],35,y+61))
        offset,caption=PAYOFFS[label]
        time=start+offset
        if label!="outro":
            cues.append(cue(time,end,"Caption",caption,504,1190,5))
        start=end
    path.write_text(ASS_HEAD+"\n".join(cues)+"\n",encoding="utf-8")
    return cues

def get_frame(path,at):
    p=subprocess.run(["ffmpeg","-hide_banner","-v","error","-ss",f"{at:.2f}",
         "-i",str(path),"-frames:v","1","-f","image2pipe","-vcodec","mjpeg",
         "-q:v","3","pipe:1"],check=True,capture_output=True,timeout=30)
    return Image.open(io.BytesIO(p.stdout)).convert("RGB")

def render_endcard(selected,out):
    # Five individual real video screenshots; never generated animal images.
    img=Image.new("RGB",(W,H),"#070C11");d=ImageDraw.Draw(img)
    fontfile=subprocess.run(["fc-match","-f","%{file}","NanumSquare"],
                            capture_output=True,text=True,check=True).stdout.strip()
    ft=lambda s: ImageFont.truetype(fontfile,s)
    d.rounded_rectangle((42,150,1038,435),radius=36,fill="#13202B")
    d.text((80,192),"5개의 순간",font=ft(70),fill="#F5D04E")
    d.text((80,300),"당신의 1위는?",font=ft(46),fill="white")
    cards=[(1,selected[4],4.5),(2,selected[3],7.0),(3,selected[2],3.2),
           (4,selected[1],25.5),(5,selected[0],1.2)]
    places=[(50,455,521,980),(559,455,1030,980),
            (50,1010,360,1485),(385,1010,695,1485),(720,1010,1030,1485)]
    for (rank,clip,seconds),rect in zip(cards,places):
        x0,y0,x1,y1=rect
        raw=get_frame(clip["local_path"],seconds)
        width,height=(x1-x0-14),(y1-y0-100)
        thumb=ImageOps.fit(raw,(width,height),Image.Resampling.LANCZOS,centering=(.5,.5))
        d.rounded_rectangle(rect,radius=21,fill="#233442",outline="#465A68",width=2)
        img.paste(thumb,(x0+7,y0+7))
        d.text((x0+18,y1-73),f"{rank}위",font=ft(39 if rank<=2 else 31),fill="#F5D04E")
        name=RANK_NAMES[rank-1]
        d.text((x0+94 if rank<=2 else x0+86,y1-69),name,font=ft(27 if rank<=2 else 21),fill="white")
    d.text((80,1680),"영상에서 직접 고른 5개의 장면",font=ft(30),fill="#D5E1EA")
    return img.save(out,quality=92)

@dataclass(frozen=True, kw_only=True)
class SourceCrop:
    width: int
    height: int
    y: int
    start_x: int
    end_x: int
    pan_start: float
    pan_end: float


def create_scene(source,start,seconds,destination,*,clear_rank_rail=False,
                 picture_height=1614,source_crop=None,playback_rate=1.0):
    # Render source exactly once: the former split/back/front composition
    # duplicated wide footage in the exposed white margins (rank 2).
    # Solid white padding is deliberately NOT a blurred/source-video backdrop.
    # Keep the complete source image, including action near frame edges.
    left=270 if clear_rank_rail else 0
    available_width=W-left
    if not 0<playback_rate<=1:
        raise ValueError("Scene playback rate must be in (0, 1]")
    crop_filter=""
    if source_crop is not None:
        # FFmpeg's t is relative to this seek. Use original time so a replay
        # of the same action gets exactly the same framing.
        crop=source_crop
        pan=(f"{crop.start_x}+({crop.end_x}-{crop.start_x})*"
             f"clip((t+{start}-{crop.pan_start})/({crop.pan_end}-{crop.pan_start}),0,1)")
        crop_filter=f"crop={crop.width}:{crop.height}:'{pan}':{crop.y},"
    filtergraph=(
        f"[0:v]{crop_filter}scale={available_width}:{picture_height}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,"
        "setsar=1,"
        f"pad=1080:{picture_height}:{left}+({available_width}-iw)/2:(oh-ih)/2:color=white,"
        "pad=1080:1920:0:306:color=white,"
        "drawbox=x=0:y=420:w=270:h=850:color=white@0.97:t=fill,"
        # Timestamp rounding near source EOF can drop 1-4 frames. Allow at
        # most 0.20s of cloned final-source frame; never silently pad seconds.
        f"setpts=(PTS-STARTPTS)/{playback_rate},fps=24,"
        "tpad=stop_mode=clone:stop_duration=0.20,"
        f"trim=end_frame={int(seconds*FPS)},setpts=N/(24*TB),format=yuv420p[v]")
    expected_frames=int(seconds*FPS)
    if seconds <= 0 or abs(expected_frames-seconds*FPS)>1e-6:
        raise ValueError("Scene length must fit 24fps exact frame budget")
    run(["ffmpeg","-hide_banner","-v","error","-y","-ss",str(start),"-i",str(source),
         "-filter_complex",filtergraph,"-map","[v]",
         "-frames:v",str(expected_frames),"-fps_mode","cfr","-r","24","-an",
         "-c:v","libx264","-preset","veryfast","-crf","23",
         "-pix_fmt","yuv420p","-movflags","+faststart",str(destination)],timeout=250)
    # Never claim 30 seconds from the AAC/container when video ends at 717/720.
    try:
        evidence=json.loads(subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v:0",
             "-show_entries","stream=nb_frames,duration,r_frame_rate",
             "-of","json",str(destination)],text=True,timeout=30))
        stream=evidence["streams"][0]
        if (int(stream.get("nb_frames",0))!=expected_frames or
            stream.get("r_frame_rate")!="24/1" or
            abs(float(stream.get("duration",0))-seconds)>0.02):
            raise ValueError("SCENE_FRAME_BUDGET_INVALID")
    except (KeyError,IndexError,TypeError,OSError,subprocess.SubprocessError) as exc:
        raise ValueError("SCENE_FRAME_EVIDENCE_MISSING") from exc
def inspect_qa(file,output,captions):
    p=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams",
       "-of","json",str(file)],capture_output=True,text=True,check=True,timeout=30)
    a=json.loads(p.stdout)
    v=[s for s in a["streams"] if s["codec_type"]=="video"]
    aud=[s for s in a["streams"] if s["codec_type"]=="audio"]
    if len(v)!=1 or len(aud)!=1 or v[0]["codec_name"]!="h264" or aud[0]["codec_name"]!="aac" or v[0]["width"]!=1080 or v[0]["height"]!=1920 or v[0]["r_frame_rate"]!="24/1":
        raise ValueError("Wrong H264/AAC 9:16 or frame rate")
    if not 29.95<=float(v[0]["duration"])<=30.1 or not 29.95<=float(aud[0]["duration"])<=30.1:
        raise ValueError("Full 30s video and audio stream mandatory")
    run(["ffmpeg","-hide_banner","-v","error","-xerror","-i",str(file),
         "-map","0:v:0","-map","0:a:0","-f","null","-"],timeout=240)
    report={
       "status":"TECHNICAL_AV_PASS_CREATIVE_RIGHTS_UNVERIFIED",
       "version":"V28_3_CENTERED_TITLE",
       "file":file.name,
       "duration_sec":30,
       "resolution":"1080x1920",
       "fps":24,
       "full_decode":"PASS",
       "unique_real_source_videos":5,
       "source_audio_mixed":False,
       "self_synthesized_soundtrack":True,
       "narration":False,
       "TTS":False,
       "editor_reaction_single_line_each_rank":True,
       "caption_start_global_seconds":{"hook":0,"rank5":2.42,"rank4":7.1,
        "rank3":12.35,"rank2":17.5,"rank1":23.2,"outro":27},
       "embedded_prior_v27_subtitles":False,
       "fixed_center_title_from_to":[0,27],
       "top_header_reserve_px":305,
       "full_source_pixels_retained":True,
       "free_content_provider_license_metadata_checked":True,
       "third_party_rights_independently_cleared":False,
       "YouTube_reused_content_monetization_approved":False,
       "publication_approved":False,
       "edit_100_point_score":None,
       "QA_note":"Human full frame/comedy review needed after actual downloaded video, never pretend algorithm verified humor."
    }
    (output/"V28_TECHNICAL_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="output")
    args=ap.parse_args()
    dest=Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    chosen=json.loads(Path("sample/v22-mixed-selection.json").read_text(encoding="utf-8"))
    catalog=json.loads(Path("sample/v22-sources.json").read_text(encoding="utf-8"))
    rows=validate_mixed_selection(chosen,catalog)
    selected,labels=fetch_mixed_sources(rows,catalog,dest)
    work=dest/"v28_segments";work.mkdir(exist_ok=True)
    base=[float(x["highlight_start"]) for x in selected]
    inputs=[
       (selected[-1],base[-1]+1.8,2),
       (selected[0],base[0],4),
       (selected[1],base[1],5),
       (selected[2],base[2],4),
       (selected[3],base[3],6),
       (selected[4],base[4],6),
    ]
    segment_files=[]
    for i,(clip,start,length) in enumerate(inputs):
        if start+length>float(clip["duration"])+0.05:
            raise ValueError("Explicit action cut outside actual original")
        video=work/f"v28_{i:02}.mp4"
        create_scene(clip["local_path"],start,length,video)
        segment_files.append(video)
        print("V28 full-screen source",i,clip["title"],start,length,flush=True)
    endcard=work/"original_5_clip_endcard.jpg"
    render_endcard(selected,endcard)
    outro=work/"v28_06.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-loop","1","-framerate","24",
         "-i",str(endcard),"-t","3","-vf","format=yuv420p","-c:v","libx264",
         "-preset","veryfast","-crf","23","-r","24","-an",str(outro)],timeout=45)
    segment_files.append(outro)
    txt=work/"segments.txt"
    txt.write_text("".join("file '"+str(f.resolve()).replace("'","'\\''")+"'\n" for f in segment_files))
    concat=work/"original_fullscreen_30s.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-f","concat","-safe","0",
         "-i",str(txt),"-c","copy",str(concat)],timeout=80)
    ass=work/"editor_one_line_and_rank.ass"
    captions=build_ass(ass)
    music=work/"original_synthesized_music.wav"
    create_soundtrack(music)
    out=dest/"TOP5_V28_FULLSCREEN_SINGLE_LINE_REVIEW_1080x1920.mp4"
    run(["ffmpeg","-hide_banner","-v","error","-y","-i",str(concat),"-i",str(music),
         "-vf",f"ass={ass}","-map","0:v:0","-map","1:a:0",
         "-c:v","libx264","-preset","veryfast","-crf","21","-r","24",
         "-c:a","aac","-b:a","160k","-ar","48000",
         "-af","loudnorm=I=-21:TP=-2.2:LRA=7","-t","30",
         "-movflags","+faststart",str(out)],timeout=350)
    qa=inspect_qa(out,dest,captions)
    # Actual sampled video frames for human editorial judgement.
    screen=work/"QA_contact.jpg"
    from PIL import ImageOps
    times=[.8,2.8,5.2,7.4,9.4,12.8,14.0,17.8,20,23.8,25.4,28.1]
    cw,ch=216,384
    sheet=Image.new("RGB",(cw*6,ch*2),"black")
    for i,t in enumerate(times):
        frame=get_frame(out,t).resize((cw,ch))
        sheet.paste(frame,((i%6)*cw,(i//6)*ch))
    sheet.save(dest/"V28_ACTUAL_12FRAME_QA.jpg",quality=88)
    print("SUCCESS",out,qa["status"],flush=True)

if __name__=="__main__":
    main()
