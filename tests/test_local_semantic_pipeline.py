"""Regression checks for optional semantic reader without real model downloads."""
from src.local_production_pipeline import run

def test_semantic_reader_not_invoked_for_rights_rejected_source(tmp_path):
    def forbidden(path):
        raise AssertionError("No semantic model call before rights preflight")
    result=run([{"id":"bad","provider":"pexels","local_path":"/missing.mp4"}],
               output_dir=tmp_path/"out",dog_weights="/missing.pt",
               semantic_reader=forbidden)
    assert result["render_eligible"] is False

def test_semantic_cli_help_imports():
    from src.local_production_pipeline import main
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
