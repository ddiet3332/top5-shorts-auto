from src.quality_gates import (
    APPROVAL_DEFAULTS, MAX_BYTES, gate_0_rights, gate_1_metadata, predownload_gate
)

def candidate(**changes):
    c = dict(id="px1", provider="pexels", source_url="https://www.pexels.com/video/1/",
             creator="Creator", license="Pexels License",
             license_url="https://www.pexels.com/license/",
             license_snapshot_sha256="a" * 64,
             size_bytes=12_000_000, duration_sec=12, width=1080, height=1920)
    c.update(changes)
    return c

def test_license_missing_fails_closed():
    assert predownload_gate(candidate(license=None)).code == "REJECT_RIGHTS_UNCLEAR"

def test_youtube_cc_requires_manual_approval():
    c = candidate(provider="youtube_cc")
    assert not gate_0_rights(c).accepted
    assert gate_0_rights(c, {"px1"}).accepted

def test_size_fails_before_download():
    assert predownload_gate(candidate(size_bytes=MAX_BYTES + 1)).code == "REJECT_SIZE"

def test_duration_fails_before_download():
    assert predownload_gate(candidate(duration_sec=61)).code == "REJECT_DURATION"

def test_resolution_fails_before_download():
    assert predownload_gate(candidate(width=640, height=1920)).code == "REJECT_RESOLUTION"

def test_missing_metadata_fails_closed():
    c = candidate()
    del c["size_bytes"]
    assert predownload_gate(c).code == "REJECT_METADATA_MISSING"

def test_pass_is_not_rights_certification():
    assert predownload_gate(candidate()).accepted
    assert APPROVAL_DEFAULTS == {
        "editorial_score_100": None, "rights_verified": False,
        "humor_certified": False, "publication_approved": False,
        "youtube_auto_upload": False,
    }
