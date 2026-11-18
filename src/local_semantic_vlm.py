"""Free local video-semantic evidence with a small open-weight VLM.

Extract three actual frames from each video; ask a local vision-language model
for setup/action/payoff. Parsing is fail-closed and NEVER certifies humor.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def extract_frames(video_path):
    import cv2
    from PIL import Image
    cap=cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("SEMANTIC_VIDEO_UNREADABLE")
    try:
        count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if count < 3:
            raise RuntimeError("SEMANTIC_VIDEO_TOO_SHORT")
        images=[]
        for index in (int(count*0.12),int(count*0.52),int(count*0.88)):
            cap.set(cv2.CAP_PROP_POS_FRAMES,index)
            ok,frame=cap.read()
            if not ok:
                raise RuntimeError("SEMANTIC_FRAME_DECODE_FAILED")
            h,w=frame.shape[:2]
            scale=min(1.0,512/max(h,w))
            frame=cv2.resize(frame,(max(1,round(w*scale)),max(1,round(h*scale))))
            images.append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
        return images
    finally:
        cap.release()

def run_semantic(video_path, model_id="HuggingFaceTB/SmolVLM-256M-Instruct"):
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from .gate3_semantic import parse_semantic_response
    frames=extract_frames(video_path)
    processor=AutoProcessor.from_pretrained(model_id)
    model=AutoModelForImageTextToText.from_pretrained(model_id,torch_dtype=torch.float32)
    model.eval()
    prompt=("These are chronological frames from a short video. Describe only what is "
            "visible. Score setup, action, payoff separately as integers 0-5, where "
            "payoff=0 if no clear visual surprise or payoff is visible. "
            "Return ONLY JSON with exactly keys setup, action, payoff.")
    messages=[{"role":"user","content":[
        {"type":"text","text":prompt},
        *[{"type":"image"} for _ in frames]]}]
    formatted=processor.apply_chat_template(messages,add_generation_prompt=True)
    inputs=processor(text=formatted,images=frames,return_tensors="pt")
    with torch.inference_mode():
        output=model.generate(**inputs,max_new_tokens=100,do_sample=False)
    response=processor.batch_decode(output[:,inputs["input_ids"].shape[1]:],skip_special_tokens=True)[0].strip()
    verdict=parse_semantic_response(response)
    return {"model_id":model_id,"raw_response":response,
            "semantic_score":verdict.semantic_score,"gate_3_passed":verdict.passed,
            "code":verdict.code,"human_humor_verified":False,
            "rights_verified":False,"publication_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--model-id",default="HuggingFaceTB/SmolVLM-256M-Instruct")
    args=p.parse_args()
    result=run_semantic(args.video,args.model_id)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
