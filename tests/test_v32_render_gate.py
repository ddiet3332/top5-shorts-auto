import hashlib
import json
import pytest
from src.v32_render_gate import validate_render_handoff, RenderGateRejected

def test_no_handoff_rejected(tmp_path):
    with pytest.raises(RenderGateRejected):
        validate_render_handoff(tmp_path/"missing.json",[],{})

def test_mismatch_rejected(tmp_path):
    rows=[]
    for i in range(6):
        p=tmp_path/f"{i}.mp4"
        p.write_bytes(f"video-{i}".encode())
        rows.append({"local_path":str(p),**{f"gate_{j}_passed":True for j in range(4)}})
    payload={"status":"SIX_SOURCES_GATE_PASSED_PENDING_EDITORIAL_AND_RIGHTS",
             "ranked":rows[:5],"hook":rows[5],
             "source_sha256":[hashlib.sha256((f"video-{i}").encode()).hexdigest() for i in range(6)]}
    path=tmp_path/"handoff.json"
    path.write_text(json.dumps(payload))
    assert validate_render_handoff(path,rows[:5],rows[5])["publication_approved"] is False
    with pytest.raises(RenderGateRejected,match="RENDER_SELECTION_NOT_QUALIFIED"):
        validate_render_handoff(path,rows[1:6],rows[0])
