import json
from src.free_gate_runner import evaluate_candidate, evaluate_manifest

def candidate():
    return {"id":"p1","provider":"pexels","source_page":"https://example.com/clip",
            "author":"author","license":"Pexels License","license_url":"https://example.com/license",
            "license_snapshot_sha256":"a"*64,
            "size_bytes":100000,"duration_sec":10,"width":1080,"height":1920,
            "local_path":"/tmp/example.mp4"}

def motion(_):
    return {"static_fraction":0.1,"late_early_motion_ratio":1.5}

def dog(_):
    return {"subject_bbox_fraction":0.2,"subject_detected_fraction":0.9}

def test_missing_rights_proof_rejected_before_readers():
    c=candidate()
    del c["license_snapshot_sha256"]
    r=evaluate_candidate(c,motion_reader=lambda _: (_ for _ in ()).throw(AssertionError()),
                         dog_reader=dog)
    assert r["reject_code"]=="REJECT_RIGHTS_UNCLEAR"

def test_missing_local_models_rejected():
    assert evaluate_candidate(candidate())["reject_code"]=="REJECT_LOCAL_ANALYSIS_UNAVAILABLE"

def test_missing_semantic_model_rejected():
    r=evaluate_candidate(candidate(),motion_reader=motion,dog_reader=dog)
    assert r["gate_2_passed"] is True
    assert r["reject_code"]=="REJECT_SEMANTIC_UNAVAILABLE"

def test_semantic_response_valid_but_not_approved():
    r=evaluate_candidate(candidate(),motion_reader=motion,dog_reader=dog,
                         semantic_response='{"setup":3,"action":4,"payoff":4}')
    assert r["gate_3_passed"] is True
    assert r["editorial_score_100"] is None
    assert r["rights_verified"] is False
    assert r["publication_approved"] is False

def test_manifest_fails_closed_even_when_semantic_valid(tmp_path):
    c=candidate()
    report=evaluate_manifest([c],tmp_path/"evidence.json",motion_reader=motion,dog_reader=dog,
        semantic_responses={"p1":'{"setup":3,"action":4,"payoff":4}'})
    assert report["status"]=="INSUFFICIENT_QUALIFIED_SOURCES"
    assert json.loads((tmp_path/"evidence.json").read_text())["publication_approved"] is False
