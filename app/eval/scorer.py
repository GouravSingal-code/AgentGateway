"""Accuracy scoring: exact match + keyword overlap (no heavy ML dependency required)."""


def score_output(output: str, expected_contains: list[str]) -> float:
    if not expected_contains:
        return 1.0
    output_lower = output.lower()
    hits = sum(1 for phrase in expected_contains if phrase.lower() in output_lower)
    return round(hits / len(expected_contains), 4)


def score_tool_calls(actual_tools: list[dict], expected_tools: list[str]) -> float:
    if not expected_tools:
        return 1.0
    actual_names = {tc["tool"] for tc in actual_tools}
    hits = sum(1 for t in expected_tools if t in actual_names)
    return round(hits / len(expected_tools), 4)


def combined_score(output_score: float, tool_score: float) -> float:
    return round((output_score + tool_score) / 2, 4)
