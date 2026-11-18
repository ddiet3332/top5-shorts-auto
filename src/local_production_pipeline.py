"""End-to-end local-only evidence pipeline: Gate 0-3 -> six-source V32 handoff.

Requires existing videos, local detector weights and externally produced
semantic responses. It never downloads model weights or certifies rights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .free_gate_runner import evaluate_manifest
from .local_motion_metrics import extract_motion_metrics
from .local_dog_detector import detect_dog_metrics
from .verified_v32_handoff import verified_handoff
from .v32_render_gate import validate_render_handoff, RenderGateRejected

def run(candidates, *, output_dir, dog_weights, semantic_responses=None,
        motion_reader=extract_motion_metrics, dog_reader=None):
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    if dog_reader is None:
        dog_reader=lambda path: detect_dog_metrics(path,dog_weights)
    gate=evaluate_manifest(candidates,output/"GATE_RESULTS.json",
                           motion_reader=motion_reader,dog_reader=dog_reader,
                           semantic_responses=semantic_responses or {})
    handoff=verified_handoff(candidates,gate["candidates"],
                              output/"VERIFIED_V32_HANDOFF.json")
    if handoff["status"].startswith("SIX_SOURCES"):
        try:
            validate_render_handoff(output/"VERIFIED_V32_HANDOFF.json",
                                    handoff["ranked"],handoff["hook"])
        except RenderGateRejected:
            handoff["status"]="INSUFFICIENT_QUALIFIED_SOURCES"
            handoff["ranked"]=[]
            handoff["hook"]=None
            (output/"VERIFIED_V32_HANDOFF.json").write_text(
                json.dumps(handoff,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"status":handoff["status"],"qualified_count":gate["qualified_count"],
            "render_eligible":handoff["status"].startswith("SIX_SOURCES"),
            "publication_approved":False}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--candidates",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--dog-weights",required=True)
    p.add_argument("--semantic-responses")
    a=p.parse_args(argv)
    candidates=json.loads(Path(a.candidates).read_text(encoding="utf-8"))
    if isinstance(candidates,dict):
        candidates=candidates.get("candidates",[])
    if not isinstance(candidates,list):
        raise ValueError("CANDIDATE_MANIFEST_INVALID")
    responses={}
    if a.semantic_responses:
        responses=json.loads(Path(a.semantic_responses).read_text(encoding="utf-8"))
    result=run(candidates,output_dir=a.output_dir,dog_weights=a.dog_weights,
               semantic_responses=responses)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["render_eligible"] else 2

if __name__=="__main__":
    raise SystemExit(main())
