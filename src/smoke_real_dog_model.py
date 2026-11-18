"""Run genuine local pretrained dog detection on a generated smoke video.

This checks inference availability, not detection accuracy, editorial value,
rights clearance or final video production.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--weights",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    import cv2
    import numpy as np
    from .local_dog_detector import detect_dog_metrics
    weights=Path(a.weights)
    if not weights.is_file() or weights.stat().st_size==0:
        raise RuntimeError("MODEL_WEIGHTS_MISSING")
    output=Path(a.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    video=output.parent/"MODEL_SMOKE_SYNTHETIC.mp4"
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*"mp4v"),6,(720,1280))
    if not writer.isOpened():
        raise RuntimeError("SMOKE_VIDEO_WRITER_UNAVAILABLE")
    for i in range(12):
        frame=np.zeros((1280,720,3),dtype=np.uint8)
        cv2.rectangle(frame,(100+i*12,350),(450+i*12,750),(255,255,255),-1)
        writer.write(frame)
    writer.release()
    result=detect_dog_metrics(video,weights,sample_fps=3)
    sha=hashlib.sha256(weights.read_bytes()).hexdigest()
    payload={"model_sha256":sha,"model_bytes":weights.stat().st_size,
             "synthetic_video":str(video),"inference_executed":True,
             "metrics":result,"real_dog_source_verified":False,
             "rights_verified":False,"publication_approved":False}
    output.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload))
if __name__=="__main__":
    main()
