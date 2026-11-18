"""V32 render gate: validate actual six-source handoff against selected paths.

Never trust a handoff JSON alone: recompute SHA256 from files and ensure
five ranked source paths and the independent hook match the exact handoff.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

class RenderGateRejected(RuntimeError):
    pass

def _sha(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size <= 0:
        raise RenderGateRejected("SOURCE_MISSING")
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def validate_render_handoff(handoff_path, ranked_sources, hook_source):
    try:
        payload=json.loads(Path(handoff_path).read_text(encoding="utf-8"))
        if payload.get("status")!="SIX_SOURCES_GATE_PASSED_PENDING_EDITORIAL_AND_RIGHTS":
            raise RenderGateRejected("HANDOFF_NOT_QUALIFIED")
        selected=payload["ranked"]+[payload["hook"]]
        if len(payload["ranked"])!=5 or len(selected)!=6 or len(payload["source_sha256"])!=6:
            raise RenderGateRejected("HANDOFF_COUNT_INVALID")
        actual=[_sha(row["local_path"]) for row in selected]
        if actual!=payload["source_sha256"] or len(set(actual))!=6:
            raise RenderGateRejected("HANDOFF_SHA_MISMATCH")
        expected=[_sha(row["local_path"]) for row in ranked_sources]+[_sha(hook_source["local_path"])]
        if expected!=actual:
            raise RenderGateRejected("RENDER_SELECTION_NOT_QUALIFIED")
        if any(not all(row.get(f"gate_{i}_passed") is True for i in range(4)) for row in selected):
            raise RenderGateRejected("HANDOFF_GATE_MISSING")
        return {"render_eligible":True,"publication_approved":False,
                "rights_verified":False,"editorial_score_100":None}
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        raise RenderGateRejected("HANDOFF_INVALID") from exc
