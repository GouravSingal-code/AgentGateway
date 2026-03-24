"""LangGraph-based multi-step agent executor."""
import time
import uuid
from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from app.agent.prompts import SYSTEM_PROMPT
from app.config import settings
from app.observability.cost import compute_cost
from app.tools.registry import execute_tool, get_all_tools, get_tool_schema

logger = structlog.get_logger()


def _build_lc_tool(tool_name: str) -> StructuredTool:
    schema = get_tool_schema(tool_name)
    if not schema:
        raise ValueError(f"Tool not found: {tool_name}")

    async def _run(**kwargs) -> str:
        result = await execute_tool(tool_name, kwargs)
        return str(result)

    return StructuredTool.from_function(
        coroutine=_run,
        name=tool_name,
        description=schema["description"],
    )


def _get_llm(model: str):
    if "claude" in model:
        return ChatAnthropic(model=model, api_key=settings.anthropic_api_key)
    return ChatOpenAI(model=model, api_key=settings.openai_api_key)


async def run_agent(
    prompt: str,
    tools: list[str],
    model: str,
    max_steps: int,
    tenant_id: uuid.UUID,
    db: Any,
) -> dict:
    start = time.monotonic()

    # Use all registered tools if none specified
    tool_names = tools or [t["name"] for t in get_all_tools()]
    lc_tools = [_build_lc_tool(name) for name in tool_names]

    llm = _get_llm(model)
    agent = create_react_agent(llm, lc_tools)

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
    result = await agent.ainvoke({"messages": messages}, {"recursion_limit": max_steps * 2})

    latency_ms = int((time.monotonic() - start) * 1000)

    # Extract output and tool calls
    final_message = result["messages"][-1]
    output = final_message.content if hasattr(final_message, "content") else str(final_message)

    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"tool": tc["name"], "args": tc["args"]})

    # Token usage
    tokens_in = 0
    tokens_out = 0
    for msg in result["messages"]:
        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            tokens_in += msg.usage_metadata.get("input_tokens", 0)
            tokens_out += msg.usage_metadata.get("output_tokens", 0)

    cost_usd = compute_cost(model, tokens_in, tokens_out)

    logger.info(
        "agent_executed",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        tool_calls=len(tool_calls),
    )

    return {
        "output": output,
        "tool_calls": tool_calls,
        "tokens_used": {"input": tokens_in, "output": tokens_out},
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
    }
