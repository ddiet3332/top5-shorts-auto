"""Fail-closed rate-limit behavior; never hammer Commons after HTTP 429."""
import io
import urllib.error
from unittest.mock import patch
from src.commons_technical_probe import probe

def test_429_stops_all_subsequent_downloads(tmp_path):
    candidates=[{"id":str(i),"title":"Dog playing","source_url":"https://commons.wikimedia.org/wiki/File:Dog.webm",
        "license_raw":"CC BY 4.0","size_bytes":100,
        "download_url":"https://upload.wikimedia.org/wikipedia/commons/test.webm"} for i in range(3)]
    calls=[]
    def deny(req,timeout):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url,429,"Too many requests",{},io.BytesIO())
    with patch("src.commons_technical_probe.urllib.request.urlopen",side_effect=deny):
        result=probe({"candidates":candidates},tmp_path)
    assert result["provider_rate_limited"]
    assert len(calls)==1
    assert [x["code"] for x in result["results"]]==[
        "DEFER_PROVIDER_RATE_LIMITED","SKIP_PROVIDER_RATE_LIMITED","SKIP_PROVIDER_RATE_LIMITED"]
