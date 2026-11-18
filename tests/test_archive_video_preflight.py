import io
import json
from src.archive_video_preflight import preflight_item

class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

def fake(data):
    def open_(request,timeout):
        return Response(json.dumps(data).encode())
    return open_

def test_licensed_original_video_is_only_metadata_preflight():
    x=preflight_item("dog001",fake({"metadata":{"title":"Puppy plays with ball","creator":"Original maker",
        "licenseurl":"https://creativecommons.org/licenses/by/4.0/"},
        "files":[{"name":"dog.webm","size":"10000","source":"original"}]}))
    assert x["status"]=="PREFLIGHT_METADATA_ONLY_PENDING_DOWNLOAD_AND_RIGHTS"
    assert x["rights_verified"] is False
    assert x["files"][0]["download_url"]=="https://archive.org/download/dog001/dog.webm"

def test_no_creator_rejected():
    x=preflight_item("dog001",fake({"metadata":{"title":"Puppy plays","licenseurl":"https://creativecommons.org/licenses/by/4.0/"}}))
    assert x["status"]=="REJECT_INCOMPLETE_LICENSE_CREATOR"

def test_irrelevant_hot_dog_rejected():
    x=preflight_item("hotdog",fake({"metadata":{"title":"Hot dog eating contest"}}))
    assert x["status"]=="REJECT_IRRELEVANT_TITLE"

def test_derived_only_rejected():
    x=preflight_item("dog001",fake({"metadata":{"title":"Dog plays","creator":"Owner","licenseurl":"https://creativecommons.org/licenses/by/4.0/"},
        "files":[{"name":"derived.mp4","size":"10000","source":"derivative"}]}))
    assert x["status"]=="REJECT_NO_BOUNDED_ORIGINAL_VIDEO"

def test_oversized_video_rejected():
    x=preflight_item("dog001",fake({"metadata":{"title":"Dog plays","creator":"Owner","licenseurl":"https://creativecommons.org/licenses/by/4.0/"},
        "files":[{"name":"huge.mp4","size":str(130*1024*1024),"source":"original"}]}))
    assert x["status"]=="REJECT_NO_BOUNDED_ORIGINAL_VIDEO"
