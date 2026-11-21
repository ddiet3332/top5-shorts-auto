#!/usr/bin/env python3
"""Second, generative video-language look at real TOP5 source-bound ranked cuts.

A 256M English VLM sees 3 chronological real rendered MP4 frames per rank.
Its descriptions are *unverified candidate evidence*, not human observation,
scene-matched Korean captions, creative scores or rights clearance.
The original final MP4 is never changed and YouTube publishing is disabled.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from top5_standard_scene_review import VIDEO, source_plan
from top5_scene_evidence import sha256

MODEL_ID = "HuggingFaceTB/SmolVLM2-256M-Video-Instruct"
MODEL_LICENSE = "Apache-2.0"
PROMPT = (
    "These three frames are in chronological order from one short video, "
    "not three separate videos. Describe only visible objects and actual "
    "changes between them in two short sentences. "
    "Does something clearly happen, or is the action unclear or nearly static? "
    "Do not guess a winner, identity, location, title, joke, emotion, or what "
    "happens outside these frames. Ignore text overlays and ranking numbers."
)
RESOLUTION = (432, 288)


def checks_metadata(root: Path):
    root=Path(root)
    topic,ranks=source_plan(root)
    video=root/VIDEO
    if not video.is_file():
        raise ValueError("SOURCE_VERIFIED_RENDER_VIDEO_MISSING")
    qa=root/"TOP5_STANDARD_EDITORIAL_QA.json"
    if not qa.is_file():
        raise ValueError("SOURCE_BOUND_38FRAME_QA_MISSING")
    prior=json.loads(qa.read_text(encoding="utf-8"))
    digest=sha256(video)
    if (prior.get("topic")!=topic or
        prior.get("rendered_mp4_sha256")!=digest or
        prior.get("five_rank_source_provenance_bound") is not True or
        prior.get("publication_approved") is not False or
        prior.get("actual_video_frames_inspected")!=38):
        raise ValueError("SOURCE_OR_VIDEO_HASH_MISMATCH")
    return video,topic,ranks,digest


def rank_sample_times(rank):
    start,end=float(rank["start"]),float(rank["end"])
    if end-start<3 or end>30.1:
        raise ValueError("RANK_WINDOW_INVALID")
    margin=min(.45,(end-start)/12)
    return [round(start+margin,3),round((start+end)/2,3),round(end-margin,3)]


def extract_roi_frame(video: Path, second: float, *, ffmpeg="ffmpeg"):
    # Keep actual footage and exclude top title/rank rail wherever possible.
    # This crop is *not* guaranteed to remove all V28.3 overlay pixels.
    # Fixed at original 1080x1920 portrait coordinate system.
    command=[ffmpeg,"-nostdin","-hide_banner","-loglevel","error",
             "-ss",str(second),"-i",str(video),"-frames:v","1",
             "-vf","crop=824:556:218:680,scale=432:288",
             "-f","image2pipe","-vcodec","mjpeg","-q:v","3","pipe:1"]
    data=subprocess.run(command,capture_output=True,check=True,timeout=35).stdout
    result=Image.open(io.BytesIO(data)).convert("RGB")
    if result.size!=RESOLUTION:
        raise ValueError("RANK_FRAME_EXTRACTION_INVALID")
    return result


def pixel_change(frames):
    if len(frames)!=3 or any(x.size!=RESOLUTION for x in frames):
        raise ValueError("THREE_CHRONOLOGICAL_FRAMES_REQUIRED")
    gray=[x.convert("L").resize((108,72)) for x in frames]
    distances=[]
    for a,b in zip(gray,gray[1:]):
        stat=ImageStat.Stat(ImageChops.difference(a,b))
        distances.append(round(float(stat.mean[0]),3))
    return {"adjacent_gray_change":distances,
            "low_motion_advisory":max(distances)<3.5,
            "not_humor_or_reaction_score":True}


def conservative_rank_note(description,changes):
    clean=" ".join(str(description).split()).strip()
    if len(clean)<12 or clean.lower().startswith(("i cannot","sorry","error")):
        return "GENERATED_DESCRIPTION_TOO_WEAK_REVIEW"
    if changes["low_motion_advisory"]:
        return "GENERATED_TEXT_WITH_LOW_FRAME_CHANGE_REVIEW"
    return "GENERATED_TEXT_MUST_BE_VISUALLY_VERIFIED"


def describe_frames(model,processor,frames,*,max_new_tokens=108):
    import torch
    if len(frames)!=3:
        raise ValueError("THREE_IMAGES_REQUIRED")
    messages=[{"role":"user","content":[
        *[{"type":"image","image":x} for x in frames],
        {"type":"text","text":PROMPT},
    ]}]
    inputs=processor.apply_chat_template(
        messages,add_generation_prompt=True,tokenize=True,
        return_dict=True,return_tensors="pt")
    inputs=inputs.to("cpu")
    with torch.inference_mode():
        result=model.generate(**inputs,do_sample=False,max_new_tokens=max_new_tokens)
    length=inputs["input_ids"].shape[-1]
    output=processor.batch_decode(result[:,length:],skip_special_tokens=True)
    return output[0].strip()


def audit(root,out,*,max_ranks=5,captioner=None,frame_reader=extract_roi_frame):
    root=Path(root)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    video,topic,ranks,digest=checks_metadata(root)
    if not 1<=max_ranks<=5:
        raise ValueError("INVALID_RANK_LIMIT")
    if captioner is None:
        import torch
        from transformers import AutoProcessor,AutoModelForImageTextToText
        torch.set_num_threads(2)
        processor=AutoProcessor.from_pretrained(MODEL_ID)
        model=AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,torch_dtype=torch.float32).to("cpu").eval()
        captioner=lambda images:describe_frames(model,processor,images)
    report={
        "schema_version":1,"chosen_topic":topic,
        "rendered_video_sha256":digest,"model":MODEL_ID,
        "model_license":MODEL_LICENSE,
        "status":"VLM_DESCRIPTION_REVIEW_ONLY",
        "not_verified_observation":True,
        "video_frames_not_original_unedited_source":True,
        "score_100":None,
        "korean_caption_ready":False,
        "automatic_caption_rendered":False,
        "video_modified":False,
        "ranking_payoff_certified":False,
        "rights_cleared":False,
        "monetization_verified":False,
        "publication_approved":False,
        "rows":[],
    }
    def save():
        (out/"VLM_SCENE_DESCRIPTION_REVIEW.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for rank in ranks[:max_ranks]:
        times=rank_sample_times(rank)
        frames=[frame_reader(video,t) for t in times]
        changes=pixel_change(frames)
        text=captioner(frames)
        finding={
            "rank":rank["rank"],
            "source_sha256":rank["source_sha256"],
            "source_url":rank["source_url"],
            "source_title_for_human_review":rank["title"],
            "rendered_frame_times":times,
            "relative_frame_change":changes,
            "generated_visual_description_en":text,
            "review_code":conservative_rank_note(text,changes),
            "real_action_verified":False,
            "model_hallucination_ruled_out":False,
            "suggested_caption_ko":None,
            "original_creative_caption_approved":False,
            "publication_approved":False,
        }
        report["rows"].append(finding)
        save()
        print("VLM RANK",rank["rank"],finding["review_code"],flush=True)
    lines=[
        "# Three-frame per-rank video-language editorial hints",
        "",
        f"Model: {MODEL_ID} (Apache 2.0) | Provenance topic: {topic}",
        "",
        "**Unverified AI output. Do not present as witnessed action, fact or editorial approval.**",
        "",
        "| Rank | Visible description generated by VLM | Independent action verification |",
        "|---:|---|---|"
    ]
    for row in report["rows"]:
        desc=re.sub(r"[\n\r|]"," ",row["generated_visual_description_en"])[:350]
        lines.append(f"| {row['rank']} | {desc} | NOT VERIFIED |")
    lines.extend(["",
        "Next: compare generated statements to full original source frames; replace weak scenes,",
        "write precise Korean original captions, and re-edit. Never treat this as 85/100 or rights clearance."
    ])
    (out/"VLM_SCENE_REVIEW_QUEUE.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    save()
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-ranks",type=int,default=5)
    a=ap.parse_args()
    rep=audit(a.source,a.output,max_ranks=a.max_ranks)
    print(json.dumps({"topic":rep["chosen_topic"],
                      "ranks_analyzed":len(rep["rows"]),
                      "editorial_score":None,
                      "publication_approved":False},ensure_ascii=False))


if __name__=="__main__":
    main()
