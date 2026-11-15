#!/usr/bin/env python3
"""V25 source audio existence and licensing gate.

No original audio is auto-included. Pexels currently publishes videos without
audio. Commons CC0/CC BY clips have Opus tracks, but an audio codec alone is
not proof of useful animal sounds or third-party clearance.
"""
from __future__ import annotations
import argparse,json,subprocess,re
from pathlib import Path

ITEMS=[
 ("rank5","pexels","PX-5495527","mixed_01.mp4","Pexels License"),
 ("rank4","pexels","PX-9208508","mixed_02.mp4","Pexels License"),
 ("rank3","pexels","PX-7680667","mixed_03.mp4","Pexels License"),
 ("rank2","wikimedia","File:Cat Jumpscare.webm","mixed_04.webm","CC0 1.0"),
 ("rank1","wikimedia","File:Salto - Cat Jump.webm","mixed_05.webm","CC BY 3.0"),
]

def inspect(source:Path,kind:str,source_id:str,license_name:str):
    d={"id":source_id,"provider":kind,"license_label":license_name,
       "source_file_found":source.is_file(),"audio_tracks":0,
       "original_audio_used_in_v25":False,
       "editorial_audio_verified":False,
       "third_party_music_and_voices_cleared":False,
       "source_audio_policy":"EXCLUDE_UNVERIFIED"}
    if not source.is_file():
        d["error"]="ORIGINAL_FILE_MISSING"
        return d
    x=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(source)],
                     text=True,capture_output=True,check=True,timeout=35)
    m=json.loads(x.stdout)
    audio=[s for s in m.get("streams",[]) if s.get("codec_type")=="audio"]
    d["audio_tracks"]=len(audio)
    d["audio_codecs"]=[s.get("codec_name") for s in audio]
    d["original_duration_sec"]=float(m.get("format",{}).get("duration",0))
    if kind=="pexels":
        d["source_audio_policy"]="NO_PEXELS_AUDIO_OR_IGNORE_UNEXPECTED_TRACK"
    elif audio:
        d["source_audio_policy"]="AVAILABLE_CODEC_BUT_HUMAN_LISTENING_AND_RIGHTS_GATE_REQUIRED"
    else:
        d["source_audio_policy"]="NO_TRACK"
    if audio:
        # Numerical signal levels only: NOT reliable human voice/music recognition.
        out=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(source),
                            "-map","0:a:0","-t","10","-af","volumedetect",
                            "-vn","-f","null","-"],capture_output=True,text=True,timeout=40)
        match=re.search(r"mean_volume:\s*(-?[0-9.]+) dB",out.stderr)
        d["source_mean_dbfs"]=float(match.group(1)) if match else None
    return d

def run(input_dir:Path,output:Path):
    rows=[]
    for rank,provider,source_id,filename,license in ITEMS:
        row=inspect(input_dir/filename,provider,source_id,license)
        row["rank"]=rank
        rows.append(row)
    d={"schema_version":1,"mode":"V25_NO_VOICE_SOURCE_AUDIO_AUDIT",
       "status":"SOURCE_AUDIO_NOT_AUTO_CLEARED",
       "original_audio_in_final_master":False,
       "final_audio":"Only previously independently synthesized audio and SFX",
       "sources":rows,
       "publication_approved":False,
       "note":"A source audio codec proves an audio track exists, not that it is copyright-clean or funny. Pexels official help says all Pexels videos are published without audio."}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V25 original audio audit:",[(x['rank'],x["audio_tracks"],x["source_audio_policy"]) for x in rows])
    return d

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--clips",default="output/clips")
    p.add_argument("--output",default="output/V25_SOURCE_AUDIO_AUDIT.json")
    a=p.parse_args()
    run(Path(a.clips),Path(a.output))
