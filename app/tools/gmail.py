"""Gmail integration via Gmail API (OAuth2 token assumed pre-authorized)."""
import base64
from email.mime.text import MIMEText

import httpx
import structlog

from app.tools.registry import register_tool

logger = structlog.get_logger()
_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def gmail_send_email(to: str, subject: str, body: str, oauth_token: str) -> dict:
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_BASE}/messages/send",
            json={"raw": raw},
            headers=_auth_headers(oauth_token),
        )
        r.raise_for_status()
        return {"id": r.json()["id"], "status": "sent"}


async def gmail_read_inbox(max_results: int = 10, oauth_token: str = "") -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/messages",
            params={"labelIds": "INBOX", "maxResults": max_results},
            headers=_auth_headers(oauth_token),
        )
        r.raise_for_status()
        messages = r.json().get("messages", [])
        return {"messages": messages, "count": len(messages)}


async def gmail_search(query: str, max_results: int = 10, oauth_token: str = "") -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/messages",
            params={"q": query, "maxResults": max_results},
            headers=_auth_headers(oauth_token),
        )
        r.raise_for_status()
        messages = r.json().get("messages", [])
        return {"messages": messages, "count": len(messages)}


# Register tools
register_tool(
    {
        "name": "gmail_send_email",
        "description": "Send an email via Gmail",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "oauth_token": {"type": "string", "description": "Tenant's Gmail OAuth2 access token"},
            },
            "required": ["to", "subject", "body", "oauth_token"],
        },
    },
    gmail_send_email,
)

register_tool(
    {
        "name": "gmail_read_inbox",
        "description": "Read messages from Gmail inbox",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "default": 10},
                "oauth_token": {"type": "string"},
            },
            "required": ["oauth_token"],
        },
    },
    gmail_read_inbox,
)

register_tool(
    {
        "name": "gmail_search",
        "description": "Search Gmail messages",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
                "oauth_token": {"type": "string"},
            },
            "required": ["query", "oauth_token"],
        },
    },
    gmail_search,
)
