import pytest
from src.qualified_selection import select_six_qualified, InsufficientQualifiedSources

def row(i, **kwargs):
    c = dict(id=f"clip-{i}", gate_0_passed=True, gate_1_passed=True,
             gate_2_passed=True, gate_3_passed=True,
             semantic_score=10.0 + i, motion_score=1.0)
    c.update(kwargs)
    return c

def digest(c):
    return f"{int(c['id'].split('-')[-1]):064x}"

def test_five_cannot_render():
    with pytest.raises(InsufficientQualifiedSources, match="INSUFFICIENT_QUALIFIED_SOURCES"):
        select_six_qualified([row(i) for i in range(5)], digest_for=digest)

def test_duplicate_hash_cannot_be_independent_hook():
    with pytest.raises(InsufficientQualifiedSources):
        select_six_qualified([row(i) for i in range(5)] + [row(4)], digest_for=digest)

def test_rejected_candidate_never_used_as_fallback():
    with pytest.raises(InsufficientQualifiedSources):
        select_six_qualified([row(i) for i in range(5)] + [row(5, gate_2_passed=False)], digest_for=digest)

def test_six_distinct_sources_and_rank_order():
    ranks, hook = select_six_qualified([row(i) for i in range(6)], digest_for=digest)
    assert [r["id"] for r in ranks] == ["clip-5", "clip-4", "clip-3", "clip-2", "clip-1"]
    assert hook["id"] == "clip-0"
