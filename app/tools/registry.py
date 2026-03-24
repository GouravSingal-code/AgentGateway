"""MCP-compatible tool registry. Each tool exposes a JSON schema and an executor."""
from typing import Any, Callable

_TOOLS: dict[str, dict] = {}
_EXECUTORS: dict[str, Callable] = {}


def register_tool(schema: dict, executor: Callable):
    name = schema["name"]
    _TOOLS[name] = schema
    _EXECUTORS[name] = executor


def get_all_tools() -> list[dict]:
    return list(_TOOLS.values())


def get_tool_schema(name: str) -> dict | None:
    return _TOOLS.get(name)


async def execute_tool(name: str, args: dict) -> Any:
    if name not in _EXECUTORS:
        raise ValueError(f"Unknown tool: {name}")
    return await _EXECUTORS[name](**args)


# Auto-register all tools on import
from app.tools import github, notion, gmail, linear  # noqa: E402, F401
