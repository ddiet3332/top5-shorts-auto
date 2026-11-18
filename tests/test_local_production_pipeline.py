import json
from src.local_production_pipeline import run

def test_missing_rights_fail_closed(tmp_path):
    c=[{"id":"demo","provider":"pexels","local_path":str(tmp_path/"missing.mp4")}]
    def no_model(path):
        raise AssertionError("invalid source must never reach inference")
    result=run(c,output_dir=tmp_path/"out",dog_weights="missing.pt",
               dog_reader=no_model,motion_reader=no_model)
    assert result["status"]=="INSUFFICIENT_QUALIFIED_SOURCES"
    assert result["render_eligible"] is False
    assert result["publication_approved"] is False
    gate=json.loads((tmp_path/"out"/"GATE_RESULTS.json").read_text())
    assert gate["candidates"][0]["reject_code"]=="REJECT_RIGHTS_UNCLEAR"
    handoff=json.loads((tmp_path/"out"/"VERIFIED_V32_HANDOFF.json").read_text())
    assert handoff["ranked"]==[]
