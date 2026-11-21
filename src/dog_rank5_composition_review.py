"""Reproducible full 30s TOP5 editorial preview with rank5 replaced ONLY.

Runs only for a separately audited Pexels original-derived 5s HD source.
Never mutates the approved/production video filename, uploads to YouTube, or
asserts licensing/monetization clearance. All outputs NOT FOR PUBLICATION.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw,ImageFont

RANK5_ID="PX-5263686"
OUTPUT_BASENAME="TOP5_DOG_RANK5_REPLACED_EDITORIAL_REVIEW_NOT_FOR_PUBLICATION.mp4"


def probe_video(path):
    result=subprocess.run(["ffprobe","-v","error","-show_entries",
                           "stream=codec_name,width,height,nb_frames:format=duration",
                           "-of","json",str(path)],capture_output=True,text=True,
                          check=True,timeout=20)
    return json.loads(result.stdout)


def validate_inputs(base,rank5,rank5_report):
    meta=json.loads(Path(rank5_report).read_text(encoding="utf-8"))
    if (meta.get("id")!=RANK5_ID or meta.get("status")!="HD_REVIEW_READY"
        or meta.get("rank")!="rank5" or meta.get("render_from_original") is not True
        or meta.get("original_matches_prior_download") is not True
        or meta.get("source_audio_copied") is not False
        or meta.get("rights_status")!="UNVERIFIED"
        or meta.get("publication_approved") is not False
        or Path(rank5).name!=meta.get("review_video_file")
        or meta.get("technical_review",{}).get("full_decode")!="PASS"):
        raise ValueError("RANK5_EDITORIAL_REVIEW_INPUT_NOT_VALIDATED")
    for path,duration,frames in ((base,30.0,720),(rank5,5.0,120)):
        info=probe_video(path)
        stream=next((s for s in info.get("streams",[]) if s.get("codec_name")=="h264"),None)
        if (not stream or int(stream.get("width",0))!=1080 or
            int(stream.get("height",0))!=1920 or
            int(stream.get("nb_frames",0))!=frames or
            abs(float(info["format"]["duration"])-duration)>0.04):
            raise ValueError("SOURCE_VIDEO_TECHNICAL_VALIDATION_FAILED")
    return meta


def make_overlay(caption,output,fontfile):
    img=Image.new("RGBA",(1080,1920),(0,0,0,0))
    d=ImageDraw.Draw(img)
    font=ImageFont.truetype(str(fontfile),55)
    body=ImageFont.truetype(str(fontfile),48)
    d.rectangle((0,388,160,988),fill=(0,0,0,172))
    for i in range(1,5):
        y=388+i*120
        d.line((0,y,160,y),fill=(15,15,15,170),width=3)
    for i in range(1,6):
        word=f"{i}위"
        bounds=d.textbbox((0,0),word,font=font,stroke_width=3)
        width,height=bounds[2]-bounds[0],bounds[3]-bounds[1]
        color=(255,210,45,255) if i==5 else (255,255,255,255)
        d.text(((160-width)/2,390+(i-1)*120+(120-height)/2-5),
               word,font=font,fill=color,stroke_width=3,
               stroke_fill=(0,0,0,255))
    bounds=d.textbbox((0,0),caption,font=body,stroke_width=5)
    width=bounds[2]-bounds[0]
    d.text(((1080-width)/2,1000),caption,font=body,
           fill=(255,255,255,255),stroke_width=5,
           stroke_fill=(0,0,0,255))
    img.save(output)


def audio_bitstream_sha(path):
    p=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(path),
                      "-map","0:a:0","-c:a","copy","-f","adts","-"],
                     capture_output=True,timeout=30,check=True)
    return hashlib.sha256(p.stdout).hexdigest()


def compose(base,rank5,rank5_report,output,*,ffmpeg=None,fontfile=None):
    base,rank5,rank5_report,output=map(Path,(base,rank5,rank5_report,output))
    meta=validate_inputs(base,rank5,rank5_report)
    output.mkdir(parents=True,exist_ok=True)
    fontfile=fontfile or subprocess.check_output(
        ["fc-match","-f","%{file}","Noto Sans CJK KR:style=Bold"],text=True,timeout=10).strip()
    if not fontfile or not Path(fontfile).is_file():
        raise ValueError("KOREAN_FONT_NOT_INSTALLED")
    setup=output/"_rank5_setup.png"
    payoff=output/"_rank5_payoff.png"
    segment=output/"_rank5_segment.mp4"
    final=output/OUTPUT_BASENAME
    ffmpeg=ffmpeg or subprocess.run
    try:
        make_overlay("얌전히 엎드려 있더니",setup,fontfile)
        make_overlay("갑자기 벌러덩!",payoff,fontfile)
        command=[
            "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
            "-i",str(rank5),
            "-loop","1","-framerate","24","-i",str(setup),
            "-loop","1","-framerate","24","-i",str(payoff),
            "-filter_complex",
            "[0:v]format=yuv420p[b];[b][1:v]overlay=x=0:y=0:enable='lt(t,2)'[a];"
            "[a][2:v]overlay=x=0:y=0:enable='gte(t,2)',format=yuv420p[v]",
            "-map","[v]","-frames:v","120","-an","-c:v","libx264",
            "-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
            "-movflags","+faststart",str(segment)
        ]
        ffmpeg(command,check=True,timeout=120)
        command=[
            "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
            "-i",str(base),"-i",str(segment),
            "-filter_complex",
            "[1:v]setpts=PTS-STARTPTS+2/TB[new];[0:v][new]overlay=x=0:y=0:"
            "eof_action=pass:repeatlast=0:shortest=0:"
            "enable='gte(t,2)*lt(t,7)',format=yuv420p[v]",
            "-map","[v]","-map","0:a?","-t","30",
            "-c:v","libx264","-preset","veryfast","-crf","21","-r","24",
            "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",
            str(final)
        ]
        ffmpeg(command,check=True,timeout=360)
        info=probe_video(final)
        video=next((s for s in info.get("streams",[]) if s.get("codec_name")=="h264"),None)
        if (not video or int(video.get("width",0))!=1080 or
            int(video.get("height",0))!=1920 or
            int(video.get("nb_frames",0))!=720 or
            abs(float(info["format"]["duration"])-30.0)>.05):
            raise ValueError("COMPOSITE_VIDEO_INVALID")
        subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(final),
                        "-f","null","-"],check=True,timeout=150,
                       stdout=subprocess.DEVNULL)
        audio_same=audio_bitstream_sha(base)==audio_bitstream_sha(final)
        if not audio_same:
            raise ValueError("REVIEW_AUDIO_MUST_MATCH_BASELINE")
        with final.open("rb") as fd:
            digest=hashlib.file_digest(fd,"sha256").hexdigest()
        report={
            "status":"EDITORIAL_REVIEW_READY_NOT_FOR_PUBLICATION",
            "rank5_source_id":RANK5_ID,
            "rank5_original_source_sha256":meta.get("source_original_sha256"),
            "replaced_frame_range":[48,167],
            "original_top5_preserved":True,
            "base_audio_bitstream_identical":True,
            "audio_subjective_review":"PENDING",
            "right_to_use_video":"UNVERIFIED",
            "youtube_reused_content_compliance":"UNVERIFIED",
            "publication_approved":False,
            "video_file":final.name,"video_sha256":digest,
            "video_bytes":final.stat().st_size,
            "video_spec":"1080x1920 24fps 720 frames 30s H264/AAC",
            "full_decode":"PASS",
        }
        (output/"DOG_RANK5_30S_INTEGRATION_QA.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("DOG_RANK5_30S_REVIEW",report["status"],flush=True)
        return report
    finally:
        for p in (setup,payoff,segment):
            p.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--rank5",type=Path,required=True)
    p.add_argument("--rank5-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    compose(a.baseline,a.rank5,a.rank5_report,a.output)


if __name__=="__main__":
    main()
