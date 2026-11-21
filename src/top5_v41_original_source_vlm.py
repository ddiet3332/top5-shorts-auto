#!/usr/bin/env python3
"""Run a 500M video-language model on genuinely ORIGINAL 15 source frames.

Frames are captured from SHA-verified originals by V40 BEFORE TOP5 title/rank/
placeholder subtitles. Untrusted model wording NEVER becomes Korean captions,
a ranking payoff fact, a 100pt score, rights clearance, or publication approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from top5_original_frame_evidence import SIDE, RANK_ORDER
from top5_smolvlm2_editorial import (
    MODEL_LICENSE,CHALLENGER_MODEL_ID,PROMPT,describe_frames,checks_metadata)

def _sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):
            h.update(part)
    return h.hexdigest()

def original_motion(frames):
    if len(frames)!=3 or any(im.size!=(SIDE,SIDE) for im in frames):
        raise ValueError("ORIGINAL_THREE_SAMPLE_IMAGES_REQUIRED")
    grays=[im.convert("L").resize((96,96)) for im in frames]
    d=[]
    for a,b in zip(grays,grays[1:]):
        d.append(round(float(ImageStat.Stat(ImageChops.difference(a,b)).mean[0]),3))
    return {"adjacent_gray_change":d,
            "low_motion_advisory":max(d)<3.5,
            "not_humor_or_rank_payoff_score":True}

def load_true_original_frame_inputs(root):
    root=Path(root).resolve()
    video,topic,ranks,video_hash=checks_metadata(root)
    source_manifest=root/"V40_ORIGINAL_FRAME_MANIFEST.json"
    if not source_manifest.is_file():
        raise ValueError("V40_SOURCE_FRAME_MANIFEST_NOT_PRESENT")
    manifest=json.loads(source_manifest.read_text(encoding="utf-8"))
    if (manifest.get("topic")!=topic or
        manifest.get("original_video_frame_count")!=15 or
        manifest.get("rank_order")!=list(RANK_ORDER) or
        manifest.get("composited_top5_text_added_to_model_images") is not False or
        manifest.get("publication_approved") is not False or
        manifest.get("editorial_score_100") is not None or
        len(manifest.get("rows",[]))!=5):
        raise ValueError("ORIGINAL_EVIDENCE_UNTRUSTED_OR_INCOMPLETE")
    all_data=[]
    used_sha=set()
    for row,sr in zip(manifest["rows"],ranks,strict=True):
        if (row.get("rank")!=sr["rank"] or
            row.get("original_source_sha256")!=sr["source_sha256"] or
            row.get("source_page")!=sr["source_url"] or
            row.get("original_title")!=sr["title"] or
            row.get("source_rights_verified") is not False or
            len(row.get("image_files",[]))!=3 or
            len(row.get("original_times_seconds",[]))!=3):
            raise ValueError("ORIGINAL_FRAME_RANK_OR_PROVENANCE_INVALID")
        if row["original_source_sha256"] in used_sha:
            raise ValueError("DUPLICATED_ORIGINAL_SOURCE_SHA")
        used_sha.add(row["original_source_sha256"])
        times=row["original_times_seconds"]
        if (times!=sorted(times) or
            not all(row["original_cut_start"]<=t<=row["original_cut_end"] for t in times)):
            raise ValueError("ORIGINAL_TIMES_NOT_IN_SELECTED_SOURCE_CUT")
        frames=[]
        image_sha=[]
        for indexed,t in zip(row["image_files"],times,strict=True):
            if indexed.get("original_time_seconds")!=t:
                raise ValueError("ORIGINAL_TIME_FILE_MISMATCH")
            path=(root/str(indexed.get("relative_file",""))).resolve()
            if not path.is_relative_to(root):
                raise ValueError("ORIGINAL_FRAME_PATH_TRAVERSAL")
            if not path.is_file() or _sha(path)!=indexed.get("image_sha256"):
                raise ValueError("ORIGINAL_FRAME_SHA_MISMATCH")
            im=Image.open(path).convert("RGB")
            if im.size!=(SIDE,SIDE):
                raise ValueError("ORIGINAL_FRAME_SIZE_MISMATCH")
            image_sha.append(indexed["image_sha256"])
            frames.append(im)
        all_data.append({
            "rank":row["rank"],
            "source_sha256":row["original_source_sha256"],
            "source_url":row["source_page"],
            "source_title_for_human_review":row["original_title"],
            "original_times_seconds":times,
            "sample_jpeg_sha256":image_sha,
            "frames":frames,
        })
    return video,topic,video_hash,all_data

def run(root,out,*,captioner=None):
    root=Path(root)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    _,topic,video_hash,records=load_true_original_frame_inputs(root)
    if captioner is None:
        import torch
        from transformers import AutoProcessor,AutoModelForImageTextToText
        torch.set_num_threads(2)
        processor=AutoProcessor.from_pretrained(CHALLENGER_MODEL_ID)
        model=AutoModelForImageTextToText.from_pretrained(
            CHALLENGER_MODEL_ID,torch_dtype=torch.float32).to("cpu").eval()
        captioner=lambda frames:describe_frames(model,processor,frames)
    report={
        "schema_version":1,
        "model":CHALLENGER_MODEL_ID,
        "model_license":MODEL_LICENSE,
        "chosen_topic":topic,
        "rendered_video_sha256":video_hash,
        "sampling_method":"Three chronological original source frames per rank, not captioned TOP5 final MP4",
        "input_frames_original_source":True,
        "top5_template_text_present_in_input":False,
        "originals_can_have_other_embedded_text":True,
        "status":"V41_ORIGINAL_SOURCE_MODEL_DESCRIPTIONS_UNVERIFIED",
        "score_100":None,
        "korean_caption_ready":False,
        "real_action_verified":False,
        "source_rights_verified":False,
        "monetization_verified":False,
        "publication_approved":False,
        "rows":[],
    }
    def save():
        (out/"VLM_SCENE_DESCRIPTION_REVIEW.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for item in records:
        text=captioner(item["frames"])
        report["rows"].append({
            "rank":item["rank"],
            "source_sha256":item["source_sha256"],
            "source_url":item["source_url"],
            "source_title_for_human_review":item["source_title_for_human_review"],
            "original_source_times":item["original_times_seconds"],
            "frame_jpeg_sha256":item["sample_jpeg_sha256"],
            "generated_visual_description_en":str(text),
            "relative_frame_change":original_motion(item["frames"]),
            "real_action_verified":False,
            "model_hallucination_ruled_out":False,
            "suggested_caption_ko":None,
            "original_creative_caption_approved":False,
            "publication_approved":False,
        })
        save()
        print("V41 ORIGINAL RANK",item["rank"],"description unverified",flush=True)
    lines=[
        "# 500M original-source 15-frame visual screening",
        "",
        "Unlike V38/V39, these images come from exact downloaded original clips,",
        "not the text-bearing TOP5 30-second compositor. Each original file and JPEG is SHA-bound.",
        "",
        "**Descriptions are UNVERIFIED. Not a human visual fact, creative caption, score or rights check.**",
        "",
        "| Rank | AI description from original footage | Status |",
        "|---:|---|---|",
    ]
    for row in report["rows"]:
        desc=" ".join(row["generated_visual_description_en"].split()).replace("|","/")
        lines.append(f"| {row['rank']} | {desc[:450]} | UNVERIFIED |")
    (out/"V41_ORIGINAL_FRAME_REVIEW.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    save()
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    data=run(args.source,args.output)
    print(json.dumps({"topic":data["chosen_topic"],
                      "rank_count":len(data["rows"]),
                      "publication_approved":False},ensure_ascii=False))

if __name__=="__main__":
    main()
