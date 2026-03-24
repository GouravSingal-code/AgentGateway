from app.observability.cost import compute_cost


def test_cost_claude_sonnet():
    cost = compute_cost("claude-sonnet-4-6", tokens_in=1000, tokens_out=500)
    expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_cost_haiku():
    cost = compute_cost("claude-haiku-4-5", tokens_in=2000, tokens_out=1000)
    expected = (2000 * 0.80 + 1000 * 4.00) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_cost_unknown_model_uses_default():
    cost = compute_cost("unknown-model", tokens_in=1000, tokens_out=1000)
    assert cost > 0
