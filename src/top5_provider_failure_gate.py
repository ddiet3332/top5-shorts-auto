"""Bounded Wikimedia provider retry and diagnostic classification.

Fail-safe: a transient 429/5xx/timeout is NOT proof that the user has no
suitable footage, and must not result in blacklisting its source or a
fabricated TOP5. Helpers operate on exceptions only; no external requests.
"""
from __future__ import annotations
import time
import urllib.error

RETRIABLE_HTTP=(429,500,502,503,504)
DEFAULT_DELAYS=(2.0,5.0)

def provider_error_code(exc):
    if isinstance(exc,urllib.error.HTTPError) and exc.code in RETRIABLE_HTTP:
        return f"PROVIDER_HTTP_{exc.code}"
    if isinstance(exc,urllib.error.URLError):
        return "PROVIDER_NETWORK_UNAVAILABLE"
    if isinstance(exc,(TimeoutError,ConnectionResetError,ConnectionAbortedError)):
        return "PROVIDER_NETWORK_UNAVAILABLE"
    return None

def _pause_seconds(exc,attempt):
    if isinstance(exc,urllib.error.HTTPError):
        retry_after=exc.headers.get("Retry-After") if exc.headers else None
        if retry_after is not None:
            try:
                delay=float(retry_after)
                if 0<=delay<=20:
                    return delay
            except (TypeError,ValueError):
                pass
    return DEFAULT_DELAYS[attempt]

def download_with_bounded_retry(downloader,source,destination,*,sleeper=time.sleep):
    """Three calls max, only on transient provider failures; no infinite loop."""
    for attempt in range(3):
        try:
            return downloader(source,destination)
        except Exception as exc:
            code=provider_error_code(exc)
            if not code or attempt>=2:
                raise
            sleeper(_pause_seconds(exc,attempt))
