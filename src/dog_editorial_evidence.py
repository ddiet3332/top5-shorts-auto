"""Objective editorial evidence for the scoped Issue 130 dog edit."""
from itertools import combinations
import io
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from dog_run_evidence import digest
from v28_fullscreen_builder import SourceCrop

BASELINE_SHA = "23f626c8855f26953d8dab7a8688fbe00e89d040b51da19fee1525ee9cfdc9db"
CROP_KEYS = ("width","height","y","start_x","end_x","pan_start","pan_end")
LABELS = ("hook","rank5","rank4","rank3","rank2","rank1","outro")


def shot(row, spec):
    if row["source_id"] != spec["source_id"]:
        raise ValueError("UNEXPECTED_SOURCE_FOR_REVIEWED_EDIT")
    return {**row, "playback_rate":spec.get("rate",1.0),
            "source_crop":SourceCrop(**dict(zip(CROP_KEYS,spec["crop"],strict=True))) if "crop" in spec else None}


def projected_occupancy(row, bbox, timestamp, rail):
    width,height = row["source_width"],row["source_height"]
    crop = row.get("source_crop")
    left,top,cw,ch = 0,0,width,height
    if crop:
        ratio = (max(0,min(1,(timestamp-crop.pan_start)/(crop.pan_end-crop.pan_start)))
                 if crop.pan_end > crop.pan_start else 0)
        left = crop.start_x+(crop.end_x-crop.start_x)*ratio
        top,cw,ch = crop.y,crop.width,crop.height
    x1,y1,x2,y2 = bbox
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("INVALID_MANUAL_BOUNDING_BOX")
    dx = max(0,min(x2*width,left+cw)-max(x1*width,left))
    dy = max(0,min(y2*height,top+ch)-max(y1*height,top))
    scale = min((810 if rail else 1080)/cw,1320/ch)
    retained = dx*dy/((x2-x1)*(y2-y1)*width*height)
    area = dx*dy*scale**2/(1080*1920)
    return {"visible_bbox_area_fraction":round(area,4),"bbox_retained_fraction":round(retained,4),
            "phone_width_px":round(dx*scale/3,1),"phone_height_px":round(dy*scale/3,1)}


def seconds(ass):
    hours,minutes,sec = ass.split(":")
    return int(hours)*3600+int(minutes)*60+float(sec)


def captions(path):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Dialogue: ") and line.split(",",4)[3] == "Caption":
            fields = line.split(",",9)
            result.append((round(seconds(fields[1]),2),round(seconds(fields[2]),2),
                           re.sub(r"\{[^}]*\}","",fields[-1])))
    return result


def expected_cues(layout):
    result = []
    for label,start,length,row,_ in layout:
        cues = row.get("caption_sequence") if label.startswith("rank") else None
        if not cues:
            offset = min(1.1,length*.22) if label.startswith("rank") else 0
            cues = [(offset,row["caption"])]
        for i,(offset,text) in enumerate(cues):
            stop = cues[i+1][0] if i+1<len(cues) else length
            result.append((round(start+offset,2),round(start+stop,2),text))
    return result


def sample(video,start,length):
    raw = subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(video),
         "-t",str(length),"-an","-vf","crop=810:1320:270:306,fps=4,scale=64:48,format=gray",
         "-f","rawvideo","-"],timeout=30)
    result = np.frombuffer(raw,np.uint8).reshape(-1,48,64).astype(np.int16)
    if len(result) < int(length*4):
        raise ValueError("SHORT_VISUAL_EVIDENCE")
    return result


def opening_motion(frames):
    changes = np.abs(np.diff(frames[:4],axis=0)).mean(axis=(1,2))
    return round(float(max(changes,default=0)),3)


def duplicate_fraction(a,b):
    distances = np.abs(a[:,None]-b[None,:]).mean(axis=(2,3))
    return round(float(min((distances.min(axis=0)<2).mean(), (distances.min(axis=1)<2).mean())),3)


def contact_sheet(video, groups, path):
    sheet = Image.new("RGB",(360*len(groups[0]),660*len(groups)),"white")
    draw = ImageDraw.Draw(sheet)
    for y,group in enumerate(groups):
        for x,(label,timestamp) in enumerate(group):
            raw = subprocess.check_output(["ffmpeg","-nostdin","-v","error","-ss",str(timestamp),
                "-i",str(video),"-frames:v","1","-vf","scale=360:640","-c:v","png","-f","image2pipe","-"],
                timeout=30)
            sheet.paste(Image.open(io.BytesIO(raw)),(x*360,y*660))
            draw.text((x*360+8,y*660+643),f"{label} {timestamp:.3f}s",fill="black")
    sheet.save(path,quality=90)


def structural_findings(layout,frames,cues,hook_motion):
    problems = []
    if cues != expected_cues(layout):
        problems.append("CAPTION_TIMESTAMP_OR_TEXT_MISMATCH")
    if hook_motion < .8:
        problems.append("WEAK_OPENING_MOTION")
    if next(length for label,_,length,_,_ in layout if label=="rank1") > 5:
        problems.append("RANK1_TOO_LONG")
    action_names = [spec["action"] for _,_,_,_,spec in layout]
    if len(set(action_names)) != len(action_names):
        problems.append("REPEATED_ACTION_LABEL")
    for (label,start,length,row,spec),(other,_,other_length,previous,_) in combinations(layout,2):
        a = row.get("hook_start",row["cut_start"])
        b = previous.get("hook_start",previous["cut_start"])
        if row["sha256"] == previous["sha256"] and max(a,b) < min(
                a+length*row["playback_rate"],b+other_length*previous["playback_rate"]):
            problems.append(f"SOURCE_WINDOW_REUSE:{label}:{other}")
        if duplicate_fraction(frames[label],frames[other]) >= .7:
            problems.append(f"VISUAL_DUPLICATE:{label}:{other}")
    return problems


def collect(video, baseline, output, layout):
    if baseline is not None and digest(baseline) != BASELINE_SHA:
        raise ValueError("BASELINE_SHA_MISMATCH")
    baseline_motion = opening_motion(sample(baseline,0,1)) if baseline else None
    actual_cues = captions(output/"work/captions.ass")
    frames = {label:sample(video,start,length) for label,start,length,_,_ in layout}
    motion = opening_motion(frames["hook"])
    problems = structural_findings(layout,frames,actual_cues,motion)
    groups, evidence = [], []
    for label,start,length,row,spec in layout:
        source_start = row.get("hook_start",row["cut_start"])
        source_end = source_start+length*row["playback_rate"]
        peak = (spec.get("payoff_sec",row["payoff_sec"])-source_start)/row["playback_rate"]
        if not 0 <= peak < length or source_end > row["duration_sec"]:
            problems.append(f"INVALID_SOURCE_TIMING:{label}")
        if label == "hook" and peak > 1:
            problems.append("LATE_HOOK_PAYOFF")
        occupancy = projected_occupancy(row,spec["box"],spec.get("payoff_sec",row["payoff_sec"]),label!="hook")
        if occupancy["visible_bbox_area_fraction"] < .022 or occupancy["bbox_retained_fraction"] < .9:
            problems.append(f"SUBJECT_OCCUPANCY_OR_PEAK_CLIPPING:{label}")
        samples = [(key,round(t,3)) for key,t in (("begin",start),("peak",start+peak),("end",start+length-1/24))]
        groups.append([(f"{label} {key}",t) for key,t in samples])
        evidence.append({"segment":label,"action_label":spec["action"],"annotated_observation":spec["observation"],
                         "source_page":row["source_page"],"source_sha256":row["sha256"],
                         "source_duration_sec":row["duration_sec"],"source_window_sec":[source_start,source_end],
                         "render_window_sec":[start,start+length],"sample_timestamps":dict(samples),
                         "payoff_relative_sec":round(peak,3),"occupancy_at_peak":occupancy,
                         "bbox_basis":"manual source-frame box projected through actual crop",
                         "semantic_action":"UNVERIFIED","semantic_caption_match":"UNVERIFIED",
                         "semantic_distinctness":"UNVERIFIED","all_frames_crop_clipping":"UNVERIFIED"})
    report = {"baseline_sha256":BASELINE_SHA,"rendered_sha256":digest(video),
              "baseline_first_second_motion":baseline_motion,"first_second_motion":motion,
              "objective_status":"FAIL" if problems else "PASS","editorial_status":"UNVERIFIED",
              "findings":problems,"segments":evidence,"publication_approved":False}
    (output/"DOG_EDITORIAL_EVIDENCE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (output/"DOG_CAPTION_TIMESTAMPS.json").write_text(json.dumps(actual_cues,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    contact_sheet(video,groups,output/"DOG_TEMPORAL_PHONE_QA.jpg")
    contact_sheet(video,[[("baseline",t) for t in (0,.25,.5,.75,1)]],output/"DOG_BASELINE_HOOK.jpg") if False else None
    contact_sheet(video,[[("new hook",t) for t in (0,.25,.5,.75,1)]],output/"DOG_FIRST_SECOND_QA.jpg")
    if baseline is not None:
        contact_sheet(baseline,[[("baseline hook",t) for t in (0,.25,.5,.75,1)]],output/"DOG_BASELINE_HOOK.jpg")
    if problems:
        raise ValueError("EDITORIAL_OBJECTIVE_GATE_FAILED: "+", ".join(problems))
    return report
