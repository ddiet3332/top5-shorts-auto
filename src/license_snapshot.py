"""Capture a genuine license-page snapshot before accepting source metadata.

Snapshots are fetched only from explicit HTTPS URLs, stored byte-for-byte,
and SHA-256 hashed. A snapshot proves what was fetched, NOT ownership,
commercial permission, or absence of third-party rights.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LicenseCaptureError('LICENSE_REDIRECT_FORBIDDEN')

class LicenseCaptureError(RuntimeError):
    pass

def snapshot_license(url: str, destination: str | Path, *, opener=None, max_bytes=2_000_000):
    parsed=urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise LicenseCaptureError("LICENSE_URL_NOT_HTTPS")
    if parsed.username or parsed.password:
        raise LicenseCaptureError("LICENSE_URL_CREDENTIALS_FORBIDDEN")
    # Restrict to known public license hosts. Never fetch arbitrary private endpoints.
    hosts={"www.pexels.com","pexels.com","pixabay.com","www.pixabay.com",
           "commons.wikimedia.org","creativecommons.org","www.creativecommons.org"}
    if parsed.hostname.lower() not in hosts:
        raise LicenseCaptureError("LICENSE_HOST_NOT_ALLOWED")
    request=Request(url,headers={"User-Agent":"TOP5-LicenseEvidence/1.0"})
    if opener is None:
        opener = build_opener(NoRedirect()).open
    try:
        with opener(request,timeout=15) as response:
            data=response.read(max_bytes+1)
            final_url=response.geturl()
    except Exception as exc:
        raise LicenseCaptureError("LICENSE_FETCH_FAILED") from exc
    if urlsplit(final_url).hostname not in hosts or urlsplit(final_url).scheme != "https":
        raise LicenseCaptureError("LICENSE_REDIRECT_NOT_ALLOWED")
    if not data or len(data)>max_bytes:
        raise LicenseCaptureError("LICENSE_RESPONSE_INVALID_SIZE")
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
    return {"license_url":url,"final_url":final_url,
            "license_snapshot_sha256":hashlib.sha256(data).hexdigest(),
            "snapshot_file":str(destination),"snapshot_bytes":len(data),
            "rights_verified":False,"publication_approved":False}
