"""Local dog-only YOLO detector, fail closed if weights/dependencies unavailable.

The model must be supplied as a local file; no automatic weight downloads.
Coordinates are measured after center-cropping to final 9:16 framing.
"""
from __future__ import annotations
from pathlib import Path
from statistics import median

class DogDetectionUnavailable(RuntimeError):
    pass

def summarize_detections(box_fractions: list[float | None]) -> dict:
    if not box_fractions:
        raise DogDetectionUnavailable("NO_SAMPLED_FRAMES")
    valid = [float(v) for v in box_fractions if v is not None and 0 <= v <= 1]
    return {
        "subject_bbox_fraction": median(valid) if valid else 0.0,
        "subject_detected_fraction": len(valid) / len(box_fractions),
        "sampled_frames": len(box_fractions),
        "subject_detector": "local_yolo_coco_dog_class_16",
    }

def detect_dog_metrics(video_path: str | Path, weights_path: str | Path, sample_fps: float = 3.0) -> dict:
    import cv2
    weights = Path(weights_path)
    if not weights.is_file() or weights.stat().st_size == 0:
        raise DogDetectionUnavailable("LOCAL_MODEL_UNAVAILABLE")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise DogDetectionUnavailable("LOCAL_DETECTOR_DEPENDENCY_UNAVAILABLE") from exc
    model = YOLO(str(weights))
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise DogDetectionUnavailable("VIDEO_UNREADABLE")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise DogDetectionUnavailable("FPS_UNAVAILABLE")
    step = max(1, round(fps / sample_fps))
    fractions = []
    i = 0
    try:
        while len(fractions) < 180:
            ok, frame = cap.read()
            if not ok:
                break
            if i % step == 0:
                height, width = frame.shape[:2]
                target_width = min(width, round(height * 9 / 16))
                x0 = (width - target_width) // 2
                crop = frame[:, x0:x0 + target_width]
                try:
                    results = model.predict(source=crop, classes=[16], conf=0.25, verbose=False)
                    boxes = results[0].boxes
                    areas = []
                    for xyxy in boxes.xyxy.cpu().numpy():
                        x1,y1,x2,y2 = xyxy
                        areas.append(max(0,x2-x1)*max(0,y2-y1)/(crop.shape[0]*crop.shape[1]))
                    fractions.append(max(areas) if areas else None)
                except Exception as exc:
                    raise DogDetectionUnavailable("DETECTOR_INFERENCE_FAILED") from exc
            i += 1
    finally:
        cap.release()
    return summarize_detections(fractions)
