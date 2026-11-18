import pytest
from src.free_inference_policy import validate_free_policy, require_local_model, FreeInferenceUnavailable

def config():
    return {"paid_api_enabled": False, "allow_network_model_api": False,
            "allow_paid_fallback": False,
            "gate2": {"provider": "local_yolo", "requires_local_weights": True},
            "gate3": {"provider": "local_vision", "requires_local_weights": True}}

def test_valid_free_only_policy():
    validate_free_policy(config())

@pytest.mark.parametrize("key", ["paid_api_enabled", "allow_network_model_api", "allow_paid_fallback"])
def test_paid_or_network_fallback_forbidden(key):
    c = config()
    c[key] = True
    with pytest.raises(ValueError):
        validate_free_policy(c)

def test_missing_local_model_fails_closed(tmp_path):
    with pytest.raises(FreeInferenceUnavailable):
        require_local_model(tmp_path / "absent.pt")
