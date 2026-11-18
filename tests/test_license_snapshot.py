import hashlib
import pytest
from src.license_snapshot import snapshot_license, LicenseCaptureError

class FakeResponse:
    def __init__(self, data, url):
        self.data=data
        self.url=url
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n): return self.data[:n]
    def geturl(self): return self.url

def test_real_bytes_hashed_and_rights_not_approved(tmp_path):
    data=b"<html>license terms</html>"
    url="https://www.pexels.com/license/"
    r=snapshot_license(url,tmp_path/"license.html",
                       opener=lambda request,timeout: FakeResponse(data,url))
    assert r["license_snapshot_sha256"]==hashlib.sha256(data).hexdigest()
    assert r["rights_verified"] is False
    assert (tmp_path/"license.html").read_bytes()==data

@pytest.mark.parametrize("url",["http://pexels.com/license/","https://localhost/license/",
                                   "https://example.com/license/"])
def test_unapproved_hosts_or_scheme_rejected(tmp_path,url):
    with pytest.raises(LicenseCaptureError):
        snapshot_license(url,tmp_path/"license.html",
                         opener=lambda request,timeout: FakeResponse(b"ok",url))

def test_redirect_target_rejected(tmp_path):
    with pytest.raises(LicenseCaptureError,match="LICENSE_REDIRECT_NOT_ALLOWED"):
        snapshot_license("https://pexels.com/license/",tmp_path/"license.html",
                         opener=lambda request,timeout: FakeResponse(b"ok","https://localhost/private"))
