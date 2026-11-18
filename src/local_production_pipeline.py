"""End-to-end local-only evidence pipeline: Gate 0-3 -> six-source V32 handoff.

Requires existing videos, local detector weights and externally produced
semantic responses. It never downloads model weights or certifies rights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .free_gate_runner import evaluate_manifest
from .quality_gates import predownload_gate
from .source_schema_adapter import normalize_v32_source
from .local_motion_metrics import extract_motion_metrics
from .local_dog_detector import detect_dog_metrics
from .verified_v32_handoff import verified_handoff
from .v32_render_gate import validate_render_handoff, RenderGateRejected

def run(candidates, *, output_dir, dog_weights, semantic_responses=None, semantic_reader=None,
        motion_reader=extract_motion_metrics, dog_reader=None):
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    if dog_reader is None:
        dog_reader=lambda path: detect_dog_metrics(path,dog_weights)
    if semantic_reader is not None:
        semantic_responses=dict(semantic_responses or {})
        for source in candidates:
            identifier=str(source.get("id") or source.get("source_page") or "")
            if identifier not in semantic_responses and predownload_gate(normalize_v32_source(source)).accepted:
                try:
                    verdict=semantic_reader(source["local_path"])
                    semantic_responses[identifier]=verdict["raw_response"]
                except (KeyError, RuntimeError, ValueError, OSError, ImportError) as exc:
                    semantic_responses[identifier]=None
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
                json.dumps(handoff,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
    return {"status":handoff["status"],"qualified_count":gate["qualified_count"],
            "render_eligible":handoff["status"].startswith("SIX_SOURCES"),
            "publication_approved":False}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--candidates",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--dog-weights",required=True)
    p.add_argument("--semantic-responses")
    p.add_argument("--run-local-semantic",action="store_true",
                   help="Run actual local VLM for missing semantic evidence (downloads model weights)")
    a=p.parse_args(argv)
    candidates=json.loads(Path(a.candidates).read_text(encoding="utf-8"))
    if isinstance(candidates,dict):
        candidates=candidates.get("candidates",[])
    if not isinstance(candidates,list):
        raise ValueError("CANDIDATE_MANIFEST_INVALID")
    responses={}
    if a.semantic_responses:
        responses=json.loads(Path(a.semantic_responses).read_text(encoding="utf-8"))
    reader=None
    if a.run_local_semantic:
        from .local_semantic_vlm import run_semantic
        reader=run_semantic
    result=run(candidates,output_dir=a.output_dir,dog_weights=a.dog_weights,
               semantic_responses=responses,semantic_reader=reader)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["render_eligible"] else 2

if __name__=="__main__":
    raise SystemExit(main())
