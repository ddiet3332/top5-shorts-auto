from src.gate2_metrics import evaluate_gate2

T = dict(min_dog_bbox_area_ratio=.08, min_dog_detection_fraction=.70,
         max_static_fraction=.30, min_late_early_motion_ratio=1.3)
M = dict(dog_bbox_area_ratio_median=.2, dog_detection_fraction=.9,
         static_fraction=.1, late_early_motion_ratio=1.8)

def check(**updates):
    return evaluate_gate2({**M, **updates}, T)

def test_static_rejected():
    assert check(static_fraction=.8).code == "REJECT_STATIC"

def test_small_subject_rejected():
    assert check(dog_bbox_area_ratio_median=.01).code == "REJECT_SUBJECT_SMALL"

def test_absent_subject_rejected():
    assert check(dog_detection_fraction=.2).code == "REJECT_SUBJECT_ABSENT"

def test_no_twist_rejected():
    assert check(late_early_motion_ratio=1.0).code == "REJECT_NO_TWIST"

def test_missing_measurement_fails_closed():
    m = dict(M)
    del m["static_fraction"]
    assert evaluate_gate2(m, T).code == "REJECT_METRICS_UNAVAILABLE"

def test_valid_metrics_only_not_humor_certification():
    assert check().passed
