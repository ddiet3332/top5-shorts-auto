import pytest
from src.local_dog_detector import summarize_detections, detect_dog_metrics, DogDetectionUnavailable

def test_summarize_detected():
    r=summarize_detections([0.1,None,0.2,0.3])
    assert r["subject_bbox_fraction"] == 0.2
    assert r["subject_detected_fraction"] == 0.75

def test_no_detection_fails_gate_by_zero_fraction():
    r=summarize_detections([None,None])
    assert r["subject_bbox_fraction"] == 0
    assert r["subject_detected_fraction"] == 0

def test_no_frames_fail_closed():
    with pytest.raises(DogDetectionUnavailable):
        summarize_detections([])

def test_no_weights_fail_closed(tmp_path):
    with pytest.raises(DogDetectionUnavailable,match="LOCAL_MODEL_UNAVAILABLE"):
        detect_dog_metrics(tmp_path/"video.mp4",tmp_path/"missing.pt")
