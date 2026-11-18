from src.gate3_semantic import parse_semantic_response

def test_invalid_json_rejected():
    assert parse_semantic_response("not-json").code == "REJECT_SEMANTIC_PARSE"

def test_missing_component_rejected():
    assert parse_semantic_response('{"setup":4,"action":4}').code == "REJECT_SEMANTIC_PARSE"

def test_out_of_range_rejected():
    assert parse_semantic_response('{"setup":6,"action":4,"payoff":4}').code == "REJECT_SEMANTIC_PARSE"

def test_boolean_not_accepted_as_integer():
    assert parse_semantic_response('{"setup":true,"action":4,"payoff":4}').code == "REJECT_SEMANTIC_PARSE"

def test_weak_payoff_rejected():
    assert parse_semantic_response('{"setup":5,"action":5,"payoff":2}').code == "REJECT_SEMANTIC_WEAK"

def test_low_total_rejected():
    assert parse_semantic_response('{"setup":2,"action":3,"payoff":3}').code == "REJECT_SEMANTIC_WEAK"

def test_valid_score_not_humor_certification():
    result = parse_semantic_response('{"setup":3,"action":4,"payoff":4}')
    assert result.passed and result.semantic_score == 11
    assert not hasattr(result, "humor_certified")
