import hashlib
from src.commons_production_readiness import assess

def test_rate_limit_is_blocked_even_with_six_rows():
    report={"provider_rate_limited":True,"results":[{"id":str(i),"technical_pass":True,
        "local_path":"/tmp/clip.webm","duration_sec":12,"width":1080,"height":1920} for i in range(6)]}
    out=assess(report)
    assert out["status"]=="BLOCKED_PROVIDER_RATE_LIMIT"
    assert out["can_render"] is False

def test_missing_real_sources_is_insufficient():
    out=assess({"results":[{"id":"1","technical_pass":False}]})
    assert out["status"]=="INSUFFICIENT_VERIFIED_MEDIA"
    assert out["qualified_distinct_count"]==0

def test_forged_metadata_cannot_unlock_six_sources():
    out=assess({"results":[{"id":str(i),"technical_pass":True,"local_path":"/nonexistent/a.webm",
        "sha256":"0"*64,"duration_sec":12,"width":1080,"height":1920} for i in range(6)]})
    assert out["status"]=="INSUFFICIENT_VERIFIED_MEDIA"
    assert out["qualified_distinct_count"]==0

def test_six_present_hash_matching_files_only_unlock_review(tmp_path):
    rows=[]
    for i in range(6):
        p=tmp_path/f"{i}.webm"
        p.write_bytes(("real-file-"+str(i)).encode())
        rows.append({"id":str(i),"technical_pass":True,"local_path":str(p),
            "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
            "duration_sec":12,"width":1080,"height":1920})
    out=assess({"results":rows})
    assert out["status"]=="READY_FOR_GATE2_GATE3_AND_RIGHTS_REVIEW"
    assert out["qualified_distinct_count"]==6
    assert out["can_render"] is False

def test_hash_mismatch_rejected(tmp_path):
    p=tmp_path/"changed.webm"
    p.write_bytes(b"changed")
    out=assess({"results":[{"id":"1","technical_pass":True,"local_path":str(p),
        "sha256":"0"*64,"duration_sec":12,"width":1080,"height":1920}]})
    assert out["qualified_distinct_count"]==0
