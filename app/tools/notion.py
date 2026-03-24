import httpx
import structlog

from app.config import settings
from app.tools.registry import register_tool

logger = structlog.get_logger()
_BASE = "https://api.notion.com/v1"
_HEADERS = {
    "Authorization": f"Bearer {settings.notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


async def notion_read_page(page_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{_BASE}/pages/{page_id}", headers=_HEADERS)
        r.raise_for_status()
        page = r.json()
        title = ""
        if "properties" in page and "title" in page["properties"]:
            title_parts = page["properties"]["title"].get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts)
        return {"id": page["id"], "title": title, "url": page.get("url", "")}


async def notion_create_page(parent_id: str, title: str, content: str = "") -> dict:
    body = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": content}}]},
            }
        ] if content else [],
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{_BASE}/pages", json=body, headers=_HEADERS)
        r.raise_for_status()
        page = r.json()
        return {"id": page["id"], "url": page.get("url", "")}


async def notion_search(query: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{_BASE}/search", json={"query": query}, headers=_HEADERS)
        r.raise_for_status()
        results = r.json().get("results", [])
        return {
            "results": [
                {"id": item["id"], "type": item["object"], "url": item.get("url", "")}
                for item in results[:10]
            ]
        }


# Register tools
register_tool(
    {
        "name": "notion_read_page",
        "description": "Read a Notion page by its ID",
        "parameters": {
            "type": "object",
            "properties": {"page_id": {"type": "string"}},
            "required": ["page_id"],
        },
    },
    notion_read_page,
)

register_tool(
    {
        "name": "notion_create_page",
        "description": "Create a new Notion page under a parent page",
        "parameters": {
            "type": "object",
            "properties": {
                "parent_id": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["parent_id", "title"],
        },
    },
    notion_create_page,
)

register_tool(
    {
        "name": "notion_search",
        "description": "Search across the Notion workspace",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    notion_search,
)
