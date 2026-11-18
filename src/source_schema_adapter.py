"""Normalize legacy V32 candidate metadata without fabricating license evidence."""
from __future__ import annotations
from typing import Any

def normalize_v32_source(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    normalized["source_url"] = row.get("source_url") or row.get("source_page") or row.get("page_url")
    normalized["creator"] = row.get("creator") or row.get("author")
    normalized["license"] = row.get("license") or row.get("license_label")
    normalized["license_snapshot_sha256"] = row.get("license_snapshot_sha256")
    normalized["provider"] = str(row.get("provider") or "").lower()
    normalized["id"] = str(row.get("id") or normalized.get("source_url") or "")
    return normalized
