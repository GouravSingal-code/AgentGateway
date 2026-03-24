from app.tools.registry import get_all_tools, get_tool_schema


def test_tools_registered():
    tools = get_all_tools()
    names = [t["name"] for t in tools]
    assert "github_list_issues" in names
    assert "github_create_issue" in names
    assert "notion_read_page" in names
    assert "linear_create_issue" in names


def test_tool_schema_has_required_fields():
    schema = get_tool_schema("github_list_issues")
    assert schema is not None
    assert "name" in schema
    assert "description" in schema
    assert "parameters" in schema
