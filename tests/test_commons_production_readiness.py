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

def test_six_real_sources_only_unlocks_next_review_not_render():
    out=assess({"results":[{"id":str(i),"technical_pass":True,"local_path":"/tmp/a.webm",
        "duration_sec":12,"width":1080,"height":1920} for i in range(6)]})
    assert out["status"]=="READY_FOR_GATE2_GATE3_AND_RIGHTS_REVIEW"
    assert out["can_render"] is False
