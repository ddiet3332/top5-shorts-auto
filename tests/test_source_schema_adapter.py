from src.source_schema_adapter import normalize_v32_source

def test_legacy_fields_normalized():
    c = normalize_v32_source({"provider":"pexels","source_page":"https://example.org/v",
                             "author":"A", "license":"Pexels License"})
    assert c["source_url"] == "https://example.org/v"
    assert c["creator"] == "A"
    assert c["license_snapshot_sha256"] is None

def test_no_fake_license_proof():
    c = normalize_v32_source({"license_url":"https://example.org/license"})
    assert c["license_snapshot_sha256"] is None

def test_explicit_proof_preserved():
    c = normalize_v32_source({"license_snapshot_sha256":"a"*64})
    assert c["license_snapshot_sha256"] == "a"*64
