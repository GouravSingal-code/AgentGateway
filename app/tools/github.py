import httpx
import structlog

from app.config import settings
from app.tools.registry import register_tool

logger = structlog.get_logger()
_BASE = "https://api.github.com"
_HEADERS = {"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json"}


async def github_list_issues(repo: str, state: str = "open") -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{_BASE}/repos/{repo}/issues", params={"state": state}, headers=_HEADERS)
        r.raise_for_status()
        issues = r.json()
        return {"issues": [{"number": i["number"], "title": i["title"], "state": i["state"]} for i in issues]}


async def github_create_issue(repo: str, title: str, body: str = "") -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/repos/{repo}/issues",
            json={"title": title, "body": body},
            headers=_HEADERS,
        )
        r.raise_for_status()
        issue = r.json()
        return {"number": issue["number"], "url": issue["html_url"], "title": issue["title"]}


async def github_get_pr_status(repo: str, pr_number: int) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{_BASE}/repos/{repo}/pulls/{pr_number}", headers=_HEADERS)
        r.raise_for_status()
        pr = r.json()
        return {"number": pr["number"], "title": pr["title"], "state": pr["state"], "mergeable": pr.get("mergeable")}


async def github_read_file(repo: str, path: str, ref: str = "main") -> dict:
    import base64
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{_BASE}/repos/{repo}/contents/{path}", params={"ref": ref}, headers=_HEADERS)
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return {"path": path, "content": content, "sha": data["sha"]}


# Register tools
register_tool(
    {
        "name": "github_list_issues",
        "description": "List GitHub issues in a repository",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo format"},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
            },
            "required": ["repo"],
        },
    },
    github_list_issues,
)

register_tool(
    {
        "name": "github_create_issue",
        "description": "Create a GitHub issue in a repository",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["repo", "title"],
        },
    },
    github_create_issue,
)

register_tool(
    {
        "name": "github_get_pr_status",
        "description": "Get the status of a GitHub pull request",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "pr_number": {"type": "integer"},
            },
            "required": ["repo", "pr_number"],
        },
    },
    github_get_pr_status,
)

register_tool(
    {
        "name": "github_read_file",
        "description": "Read a file from a GitHub repository",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "path": {"type": "string"},
                "ref": {"type": "string", "default": "main"},
            },
            "required": ["repo", "path"],
        },
    },
    github_read_file,
)
