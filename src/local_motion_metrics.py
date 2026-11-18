"""CPU-only video motion metrics, not semantic humor certification.

Frames are decoded locally via OpenCV. Translation-only camera movement is
partly compensated using phase correlation. Missing frames fail closed.
"""
from __future__ import annotations
from pathlib import Path

class MotionExtractionError(RuntimeError):
    pass

def extract_motion_metrics(video_path: str | Path, *, sample_fps: float = 3.0, static_threshold: float = 0.012) -> dict:
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise MotionExtractionError("VIDEO_UNREADABLE")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        cap.release()
        raise MotionExtractionError("FPS_UNAVAILABLE")
    step = max(1, round(fps / sample_fps))
    frames = []
    frame_index = 0
    try:
        while len(frames) < 180:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % step == 0:
                gray = cv2.cvtColor(cv2.resize(frame, (160, 284)), cv2.COLOR_BGR2GRAY)
                frames.append(gray.astype(np.float32) / 255.0)
            frame_index += 1
    finally:
        cap.release()
    if len(frames) < 3:
        raise MotionExtractionError("INSUFFICIENT_FRAMES")
    movements = []
    for prev, curr in zip(frames, frames[1:]):
        shift, response = cv2.phaseCorrelate(prev, curr)
        if not np.isfinite(shift).all():
            raise MotionExtractionError("MOTION_INVALID")
        matrix = np.float32([[1, 0, -shift[0]], [0, 1, -shift[1]]])
        aligned = cv2.warpAffine(curr, matrix, (prev.shape[1], prev.shape[0]),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        difference = float(np.mean(np.abs(prev[12:-12, 12:-12] - aligned[12:-12, 12:-12])))
        movements.append(difference)
    mid = max(1, len(movements) // 2)
    early = float(np.mean(movements[:mid]))
    late = float(np.mean(movements[mid:]))
    static_fraction = sum(x < static_threshold for x in movements) / len(movements)
    return {
        "static_fraction": round(static_fraction, 5),
        "early_motion": round(early, 6),
        "late_motion": round(late, 6),
        "late_early_motion_ratio": round(late / max(early, 0.0001), 5),
        "frames_sampled": len(frames),
        "sample_fps": round(fps / step, 4),
        "algorithm": "phase_correlation_translation_compensated_absdiff_v1",
        "subject_bbox_fraction": None,
        "subject_detected_fraction": None,
        "subject_detector": None,
    }
