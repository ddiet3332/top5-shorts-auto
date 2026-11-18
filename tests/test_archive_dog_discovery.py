"""Regression tests for Internet Archive discovery normalization and safety."""
from unittest.mock import patch
from src.archive_dog_discovery import discover

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self,*args): return False

def test_discovery_metadata_never_approves_rights():
    class Response(FakeResponse):
        def read(self,*args): return b'{"response":{"docs":[{"identifier":"dog-play","title":"Puppy play","creator":"Creator","licenseurl":"https://creativecommons.org/licenses/by/4.0/"}]}}'
    with patch("src.archive_dog_discovery.urllib.request.urlopen",return_value=Response()):
        result=discover()
    assert result["count"]==1
    assert result["candidates"][0]["source_url"]=="https://archive.org/details/dog-play"
    assert result["candidates"][0]["rights_verified"] is False
    assert result["candidates"][0]["publication_approved"] is False

def test_rejects_malicious_identifier():
    class Response(FakeResponse):
        def read(self,*args): return b'{"response":{"docs":[{"identifier":"../escape","title":"Dog"}]}}'
    with patch("src.archive_dog_discovery.urllib.request.urlopen",return_value=Response()):
        assert discover()["count"]==0

def test_unrelated_search_results_are_filtered():
    class Response(FakeResponse):
        def read(self,*args):
            return b'{"response":{"docs":[{"identifier":"celebrity","title":"Celebrity Interview"},{"identifier":"puppy-video","title":"Puppy Playing"}]}}'
    with patch("src.archive_dog_discovery.urllib.request.urlopen",return_value=Response()):
        result=discover()
    assert result["count"]==1
    assert result["candidates"][0]["id"]=="puppy-video"
