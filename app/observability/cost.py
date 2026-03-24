"""Token cost computation using approximate per-model pricing (USD per 1M tokens)."""

# Prices in USD per 1M tokens (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6":    (15.00, 75.00),
    "claude-sonnet-4-6":  (3.00,  15.00),
    "claude-haiku-4-5":   (0.80,  4.00),
    "gpt-4o":             (5.00,  15.00),
    "gpt-4o-mini":        (0.15,  0.60),
}
_DEFAULT_PRICING = (3.00, 15.00)


def compute_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return round((tokens_in * price_in + tokens_out * price_out) / 1_000_000, 6)
