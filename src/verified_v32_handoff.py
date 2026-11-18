"""Verified six-source handoff to V32; no weak candidate fallback.

The handoff is deliberately separate from rendering. Gate verdicts must be
computed by the free gate runner, never supplied by title-only ranking.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .qualified_selection import select_six_qualified, InsufficientQualifiedSources
from .quality_gates import APPROVAL_DEFAULTS

def verified_handoff(candidates, gate_results, output_path):
    decisions = {r["id"]: r for r in gate_results}
    enriched = []
    rejected = []
    for source in candidates:
        identifier = str(source.get("id") or source.get("source_url") or source.get("source_page") or "")
        decision = decisions.get(identifier)
        if not decision:
            rejected.append({"id": identifier, "code": "REJECT_NO_GATE_EVIDENCE"})
            continue
        row = dict(source)
        for index in range(4):
            row[f"gate_{index}_passed"] = decision.get(f"gate_{index}_passed") is True
        row["semantic_score"] = decision.get("semantic_score")
        row["motion_score"] = decision.get("motion_score")
        enriched.append(row)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        ranked, hook = select_six_qualified(enriched)
        selected = ranked + [hook]
        hashes = []
        for item in selected:
            digest = hashlib.sha256(Path(item["local_path"]).read_bytes()).hexdigest()
            hashes.append(digest)
        if len(set(hashes)) != 6:
            raise InsufficientQualifiedSources("INSUFFICIENT_QUALIFIED_SOURCES: duplicate hashes")
        payload = {
            "status": "SIX_SOURCES_GATE_PASSED_PENDING_EDITORIAL_AND_RIGHTS",
            "ranked": ranked, "hook": hook, "source_sha256": hashes,
            "rejected": rejected, **APPROVAL_DEFAULTS
        }
    except (InsufficientQualifiedSources, FileNotFoundError, OSError, TypeError, ValueError) as exc:
        payload = {"status": "INSUFFICIENT_QUALIFIED_SOURCES",
                   "error": str(exc), "ranked": [], "hook": None,
                   "rejected": rejected, **APPROVAL_DEFAULTS}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return payload
