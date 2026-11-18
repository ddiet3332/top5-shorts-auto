"""Pure selection of independently qualified clips; never performs publishing."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Callable, Any

class InsufficientQualifiedSources(RuntimeError):
    pass

def select_six_qualified(
    candidates: list[dict[str, Any]],
    *,
    digest_for: Callable[[dict[str, Any]], str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Only externally gated candidates with explicit pass evidence may enter.

    Returns five ranked clips (best first) and independent hook. Never
    substitutes rejected candidates or silently certifies human judgments.
    """
    def digest(candidate: dict[str, Any]) -> str:
        if digest_for is not None:
            return digest_for(candidate)
        path = Path(candidate["local_path"])
        if not path.is_file():
            raise FileNotFoundError(path)
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    eligible = []
    rejected = []
    seen = set()
    for candidate in candidates:
        identifier = str(candidate.get("id") or candidate.get("source_url") or "unknown")
        if not all(candidate.get(f"gate_{n}_passed") is True for n in range(4)):
            rejected.append({"id": identifier, "code": "REJECT_GATE_NOT_PASSED"})
            continue
        try:
            score = float(candidate["semantic_score"])
            motion = float(candidate["motion_score"])
            sha = digest(candidate)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            rejected.append({"id": identifier, "code": "REJECT_INVALID_EVIDENCE", "detail": type(exc).__name__})
            continue
        if len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
            rejected.append({"id": identifier, "code": "REJECT_INVALID_HASH"})
            continue
        if sha in seen:
            rejected.append({"id": identifier, "code": "REJECT_DUPLICATE_SOURCE"})
            continue
        seen.add(sha)
        eligible.append((score + motion, identifier, sha, candidate))
    eligible.sort(key=lambda row: (-row[0], row[1]))
    if len(eligible) < 6:
        raise InsufficientQualifiedSources(
            f"INSUFFICIENT_QUALIFIED_SOURCES: {len(eligible)}/6 distinct gate-passed originals"
        )
    ranked = [dict(row[3]) for row in eligible[:5]]
    hook = dict(eligible[5][3])
    return ranked, hook
