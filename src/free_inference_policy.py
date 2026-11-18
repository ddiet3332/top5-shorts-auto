"""Strict free-only inference policy; missing local models fail closed."""
from __future__ import annotations
import json
from pathlib import Path

class FreeInferenceUnavailable(RuntimeError):
    pass

def validate_free_policy(config: dict) -> None:
    if config.get("paid_api_enabled") is not False:
        raise ValueError("PAID_API_FORBIDDEN")
    if config.get("allow_network_model_api") is not False:
        raise ValueError("NETWORK_MODEL_API_FORBIDDEN")
    if config.get("allow_paid_fallback") is not False:
        raise ValueError("PAID_FALLBACK_FORBIDDEN")
    for gate in ("gate2", "gate3"):
        entry = config.get(gate)
        if not isinstance(entry, dict) or entry.get("requires_local_weights") is not True:
            raise ValueError("LOCAL_MODEL_REQUIRED")
        if entry.get("provider") not in {"local_yolo", "local_vision"}:
            raise ValueError("LOCAL_MODEL_REQUIRED")

def require_local_model(model_path: str | Path) -> Path:
    path = Path(model_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise FreeInferenceUnavailable("LOCAL_MODEL_UNAVAILABLE")
    return path

def load_free_policy(path: str | Path) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_free_policy(config)
    return config
