from src.verified_v32_handoff import verified_handoff

def test_no_sources_no_handoff(tmp_path):
    result=verified_handoff([],[],tmp_path/"handoff.json")
    assert result["status"]=="INSUFFICIENT_QUALIFIED_SOURCES"
    assert result["publication_approved"] is False

def test_no_gate_evidence_never_selects(tmp_path):
    result=verified_handoff([{"id":"a","local_path":"fake.mp4"}],[],tmp_path/"handoff.json")
    assert result["ranked"]==[]
    assert result["rejected"][0]["code"]=="REJECT_NO_GATE_EVIDENCE"

def test_missing_local_file_never_selects(tmp_path):
    c={"id":"a","local_path":str(tmp_path/"absent.mp4"),"semantic_score":12,"motion_score":2}
    gate={"id":"a","gate_0_passed":True,"gate_1_passed":True,"gate_2_passed":True,
          "gate_3_passed":True,"semantic_score":12,"motion_score":2}
    result=verified_handoff([c],[gate],tmp_path/"handoff.json")
    assert result["status"]=="INSUFFICIENT_QUALIFIED_SOURCES"
