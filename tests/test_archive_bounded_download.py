from src.archive_bounded_download import fetch_file, run

def test_reject_untrusted_url(tmp_path):
    x=fetch_file({"download_url":"https://example.com/evil.mp4","size":100},tmp_path/"evil.mp4")
    assert x["status"]=="REJECT_UNTRUSTED_URL"
    assert not (tmp_path/"evil.mp4").exists()

def test_reject_oversized(tmp_path):
    x=fetch_file({"download_url":"https://archive.org/download/dog/dog.mp4","size":126*1024*1024},tmp_path/"dog.mp4")
    assert x["status"]=="REJECT_SIZE"

def test_no_metadata_qualified_never_downloads(tmp_path):
    out=run({"results":[{"status":"REJECT_IRRELEVANT_TITLE"}]},tmp_path)
    assert out["attempted"]==0
    assert out["technical_pass_count"]==0
