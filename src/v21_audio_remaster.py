#!/usr/bin/env python3
"""V21.2 original synthesized soundtrack + safe loudness master.

The input already contains only licensed-source-video muted footage plus
project-synthesized transition SFX. No external music samples, narration,
or unapproved camera-recorded audio are added.

Numpy is a free build-time dependency installed by V21 workflow.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import wave
import numpy as np

SAMPLE_RATE=48000
DURATION=30.0
CUE_TIMES=(0,2,6,11,15,21,27)


def create_soundtrack(path, seed=20261115):
    sr=SAMPLE_RATE
    rng=np.random.default_rng(seed)
    n=int(sr*DURATION)
    out=np.zeros((n,2),dtype=np.float32)

    def stamp(sec, mono, pan=0.0, gain=1.0):
        idx=int(sec*sr)
        if idx<0 or idx>=n:
            return
        size=min(len(mono),n-idx)
        left=np.sqrt((1-pan)/2)
        right=np.sqrt((1+pan)/2)
        out[idx:idx+size,0]+=mono[:size]*left*gain
        out[idx:idx+size,1]+=mono[:size]*right*gain

    def kick():
        t=np.arange(int(.21*sr))/sr
        freq=77-24*np.minimum(t/.21,1)
        return np.sin(2*np.pi*np.cumsum(freq)/sr)*np.exp(-23*t)*.32

    def hat():
        t=np.arange(int(.075*sr))/sr
        noise=rng.uniform(-1,1,len(t))
        high=noise-np.convolve(noise,np.ones(12)/12,mode="same")
        return .085*high*np.exp(-47*t)

    def snap():
        t=np.arange(int(.11*sr))/sr
        return .12*rng.normal(0,1,len(t))*np.exp(-41*t)

    def chime(freq=1100,duration=.29):
        t=np.arange(int(duration*sr))/sr
        phase=2*np.pi*(freq*t+190*t*t)
        return (.12*np.sin(phase)+.035*np.sin(2*phase))*np.exp(-12*t)

    def whoosh(duration=.36):
        t=np.arange(int(duration*sr))/sr
        noise=rng.normal(0,1,len(t))
        smooth=np.convolve(noise,np.ones(45)/45,mode="same")
        return .21*smooth*(np.sin(np.pi*np.minimum(1,t/duration))**1.5)

    beat=60/114
    nbeat=int(np.ceil(DURATION/beat))
    for k in range(nbeat):
        sec=k*beat
        if k%4 in (0,2):
            stamp(sec,kick(),0,.9)
        else:
            stamp(sec,snap(),.02,.48)
        stamp(sec,hat(),-.16,.55)
        if sec+beat/2<DURATION:
            stamp(sec+beat/2,hat(),.20,.36)

    # Original, low-key two-bar plucked rhythm (not third-party music).
    notes=(523.25,659.25,587.33,783.99,659.25,587.33)
    for k in range(0,nbeat,2):
        t=np.arange(int(.31*sr))/sr
        f=notes[(k//2)%len(notes)]
        tone=(.055*np.sin(2*np.pi*f*t)+.018*np.sin(4*np.pi*f*t))*np.exp(-13*t)
        stamp(k*beat+.12,tone,-.25 if (k//2)%2 else .25,.42)

    for i,sec in enumerate(CUE_TIMES):
        stamp(sec+.035,whoosh(.24),-.3 if i%2 else .3,.78)
        stamp(sec+.11,chime(930+i*30,.26),.18 if i%2 else -.18,.92)

    # Actual source actions are aligned against V21 MP4 frame QA.
    stamp(3.45,chime(1050,.21),.2,.55)
    stamp(8.6,whoosh(.19),-.35,.57)
    stamp(12.1,whoosh(.28),.22,.95)
    stamp(17.56,whoosh(.37),.38,1.17)
    stamp(17.73,chime(1200,.23),-.35,1.3)
    stamp(23.35,whoosh(.45),-.3,1.26)
    stamp(24.8,chime(740,.27),.28,.66)

    peak=float(np.max(np.abs(out)))
    if peak>.85:
        out*=.85/peak
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(out,-.99,.99)*32767).astype(np.int16).tobytes())
    return peak


def render(input_video,final_video,scratch):
    input_video=Path(input_video)
    final_video=Path(final_video)
    scratch=Path(scratch)
    if not input_video.is_file():
        raise FileNotFoundError(input_video)
    final_video.parent.mkdir(exist_ok=True,parents=True)
    scratch.mkdir(exist_ok=True,parents=True)
    wav=scratch/"v21_original_synth.wav"
    temp=scratch/"v21_audio_mixed.mp4"
    create_soundtrack(wav)
    graph=('[0:a]volume=2.1[a0];[1:a]volume=1.0[a1];'
           '[a0][a1]amix=inputs=2:duration=longest:normalize=0,'
           'alimiter=limit=0.90,aresample=48000,'
           'atrim=0:30,asetpts=PTS-STARTPTS[aout]')
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-i",str(input_video),"-i",str(wav),
                    "-filter_complex",graph,"-map","0:v:0","-map","[aout]",
                    "-c:v","copy","-c:a","aac","-b:a","192k",
                    "-ar","48000","-movflags","+faststart",str(temp)],
                   check=True,timeout=140)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-i",str(temp),"-map","0:v:0","-map","0:a:0",
                    "-c:v","copy",
                    "-af","loudnorm=I=-21:TP=-2.2:LRA=7",
                    "-c:a","aac","-b:a","192k","-ar","48000",
                    "-t","30","-movflags","+faststart",str(final_video)],
                   check=True,timeout=140)
    # Ensure video frames and audio are genuinely valid.
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
                    "-i",str(final_video),"-f","null","-"],
                   check=True,timeout=260)
    print("V21.2 true full decode passed; original synthesized audio only.",flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="output/TOP5_DRAFT_REVIEW_ONLY_1080x1920.mp4")
    p.add_argument("--output",default="output/TOP5_V21_2_REVIEW_ONLY_1080x1920.mp4")
    p.add_argument("--scratch",default="output/v21_audio_temp")
    args=p.parse_args()
    render(args.input,args.output,args.scratch)


if __name__=="__main__":
    main()
