"""Fail-closed pre-download eligibility checks. Does not certify rights or humor."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

MIB = 1024 * 1024
MAX_BYTES = 125 * MIB
APPROVAL_DEFAULTS = {
    "editorial_score_100": None,
    "rights_verified": False,
    "humor_certified": False,
    "publication_approved": False,
    "youtube_auto_upload": False,
}
ALLOWED_PROVIDERS = {"pexels", "pixabay", "wikimedia_commons", "internet_archive", "owned", "contracted"}

@dataclass(frozen=True)
class GateDecision:
    accepted: bool
    code: str
    metrics: dict[str, Any]

def gate_0_rights(candidate: dict[str, Any], manually_approved_ids: set[str] | None = None) -> GateDecision:
    provider = str(candidate.get("provider") or "").lower()
    source_id = str(candidate.get("id") or "")
    if provider in {"youtube", "youtube_cc"} and source_id not in (manually_approved_ids or set()):
        return GateDecision(False, "REJECT_RIGHTS_UNCLEAR", {"provider": provider, "manual_approval": False})
    if provider not in ALLOWED_PROVIDERS and not (provider in {"youtube", "youtube_cc"} and source_id in (manually_approved_ids or set())):
        return GateDecision(False, "REJECT_RIGHTS_UNCLEAR", {"provider": provider})
    required = ("source_url", "creator", "license", "license_url", "license_snapshot_sha256")
    missing = [field for field in required if not candidate.get(field)]
    if missing:
        return GateDecision(False, "REJECT_RIGHTS_UNCLEAR", {"missing": missing})
    digest = str(candidate["license_snapshot_sha256"])
    if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
        return GateDecision(False, "REJECT_RIGHTS_UNCLEAR", {"invalid_license_snapshot_sha256": True})
    return GateDecision(True, "PASS_RIGHTS_METADATA_ONLY", {"provider": provider, "rights_verified": False})

def gate_1_metadata(candidate: dict[str, Any]) -> GateDecision:
    """Require trustworthy metadata before network download. No silent defaults."""
    try:
        size = int(candidate["size_bytes"])
        duration = float(candidate["duration_sec"])
        width = int(candidate["width"])
        height = int(candidate["height"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return GateDecision(False, "REJECT_METADATA_MISSING", {})
    metrics = {"size_bytes": size, "duration_sec": duration, "width": width, "height": height}
    if size <= 0 or size > MAX_BYTES:
        return GateDecision(False, "REJECT_SIZE", metrics)
    if not 5 <= duration <= 60:
        return GateDecision(False, "REJECT_DURATION", metrics)
    if min(width, height) < 720:
        return GateDecision(False, "REJECT_RESOLUTION", metrics)
    return GateDecision(True, "PASS_METADATA", metrics)

def predownload_gate(candidate: dict[str, Any], manually_approved_ids: set[str] | None = None) -> GateDecision:
    rights = gate_0_rights(candidate, manually_approved_ids)
    if not rights.accepted:
        return rights
    return gate_1_metadata(candidate)

def provenance_record(candidate: dict[str, Any], checked_at: str | None = None) -> dict[str, Any]:
    return {
        "source_url": candidate.get("source_url"),
        "creator": candidate.get("creator"),
        "license": candidate.get("license"),
        "license_url": candidate.get("license_url"),
        "license_snapshot_sha256": candidate.get("license_snapshot_sha256"),
        "collected_at": checked_at or datetime.now(timezone.utc).isoformat(),
        "rights_verified": False,
        "publication_approved": False,
    }
