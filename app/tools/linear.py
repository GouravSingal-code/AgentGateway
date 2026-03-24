import httpx
import structlog

from app.config import settings
from app.tools.registry import register_tool

logger = structlog.get_logger()
_BASE = "https://api.linear.app/graphql"
_HEADERS = {"Authorization": settings.linear_api_key, "Content-Type": "application/json"}


async def _gql(query: str, variables: dict = {}) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(_BASE, json={"query": query, "variables": variables}, headers=_HEADERS)
        r.raise_for_status()
        return r.json().get("data", {})


async def linear_create_issue(team_id: str, title: str, description: str = "") -> dict:
    data = await _gql(
        """
        mutation CreateIssue($teamId: String!, $title: String!, $description: String) {
          issueCreate(input: {teamId: $teamId, title: $title, description: $description}) {
            success
            issue { id identifier url title }
          }
        }
        """,
        {"teamId": team_id, "title": title, "description": description},
    )
    issue = data.get("issueCreate", {}).get("issue", {})
    return {"id": issue.get("id"), "identifier": issue.get("identifier"), "url": issue.get("url")}


async def linear_list_issues(team_id: str, state: str = "") -> dict:
    data = await _gql(
        """
        query Issues($teamId: String!) {
          team(id: $teamId) {
            issues { nodes { id identifier title state { name } url } }
          }
        }
        """,
        {"teamId": team_id},
    )
    issues = data.get("team", {}).get("issues", {}).get("nodes", [])
    return {"issues": [{"id": i["id"], "title": i["title"], "state": i["state"]["name"]} for i in issues]}


async def linear_update_status(issue_id: str, state_id: str) -> dict:
    data = await _gql(
        """
        mutation UpdateIssue($issueId: String!, $stateId: String!) {
          issueUpdate(id: $issueId, input: {stateId: $stateId}) {
            success
            issue { id identifier state { name } }
          }
        }
        """,
        {"issueId": issue_id, "stateId": state_id},
    )
    return data.get("issueUpdate", {})


# Register tools
register_tool(
    {
        "name": "linear_create_issue",
        "description": "Create an issue in Linear",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["team_id", "title"],
        },
    },
    linear_create_issue,
)

register_tool(
    {
        "name": "linear_list_issues",
        "description": "List issues for a Linear team",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "state": {"type": "string", "default": ""},
            },
            "required": ["team_id"],
        },
    },
    linear_list_issues,
)

register_tool(
    {
        "name": "linear_update_status",
        "description": "Update the status/state of a Linear issue",
        "parameters": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "state_id": {"type": "string"},
            },
            "required": ["issue_id", "state_id"],
        },
    },
    linear_update_status,
)
