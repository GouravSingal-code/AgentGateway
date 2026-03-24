from app.eval.scorer import combined_score, score_output, score_tool_calls


def test_score_output_full_match():
    score = score_output("Here are the open issues from GitHub", ["open issues", "GitHub"])
    assert score == 1.0


def test_score_output_partial_match():
    score = score_output("Here are the open issues", ["open issues", "GitHub"])
    assert score == 0.5


def test_score_output_no_expected():
    score = score_output("anything", [])
    assert score == 1.0


def test_score_tool_calls_match():
    actual = [{"tool": "github_list_issues", "args": {}}]
    score = score_tool_calls(actual, ["github_list_issues"])
    assert score == 1.0


def test_score_tool_calls_missing():
    actual = []
    score = score_tool_calls(actual, ["github_list_issues"])
    assert score == 0.0


def test_combined_score():
    score = combined_score(0.8, 1.0)
    assert score == 0.9
