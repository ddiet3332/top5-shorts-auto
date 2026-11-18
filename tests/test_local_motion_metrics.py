import cv2
import numpy as np
import pytest
from src.local_motion_metrics import extract_motion_metrics, MotionExtractionError

def write_video(path, moving=False):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 12, (160, 284))
    assert out.isOpened()
    for i in range(24):
        frame = np.zeros((284,160,3),dtype=np.uint8)
        x = 20 + (i * 3 if moving else 0)
        cv2.rectangle(frame,(x,80),(x+25,105),(255,255,255),-1)
        out.write(frame)
    out.release()

def test_static_video(tmp_path):
    path=tmp_path/"static.avi"
    write_video(path)
    r=extract_motion_metrics(path)
    assert r["static_fraction"] >= .8
    assert r["subject_bbox_fraction"] is None

def test_moving_video(tmp_path):
    path=tmp_path/"moving.avi"
    write_video(path,True)
    r=extract_motion_metrics(path)
    assert r["frames_sampled"] >= 3
    assert r["algorithm"].startswith("phase_correlation")
    assert r["subject_detector"] is None

def test_missing_video_fails_closed(tmp_path):
    with pytest.raises(MotionExtractionError):
        extract_motion_metrics(tmp_path/"missing.mp4")
