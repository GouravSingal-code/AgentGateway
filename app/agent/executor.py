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
from app.cache.prompt_cache import get_cached, set_cached
from app.config import settings
from app.db.models import AuditLog
from app.observability.cost import compute_cost
from app.observability.tracer import log_run, trace_tool_call
from app.tools.registry import execute_tool, get_all_tools, get_tool_schema

logger = structlog.get_logger()


def _build_lc_tool(tool_name: str, audit_entries: list, run_id_ref: list) -> StructuredTool:
    schema = get_tool_schema(tool_name)
    if not schema:
        raise ValueError(f"Tool not found: {tool_name}")

    async def _run(**kwargs) -> str:
        t0 = time.monotonic()
        status = "success"
        output = {}
        try:
            result = await execute_tool(tool_name, kwargs)
            output = result if isinstance(result, dict) else {"result": str(result)}
            return str(result)
        except Exception as e:
            status = "error"
            output = {"error": str(e)}
            raise
        finally:
            latency_ms = int((time.monotonic() - t0) * 1000)
            audit_entries.append({
                "tool_name": tool_name,
                "input_args": kwargs,
                "output": output,
                "status": status,
                "latency_ms": latency_ms,
            })

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
    run_id: uuid.UUID | None = None,
) -> dict:
    start = time.monotonic()

    # Check prompt cache first
    cached = await get_cached(model, SYSTEM_PROMPT, prompt)
    if cached:
        logger.info("prompt_cache_hit", model=model)
        return {**cached, "cache_hit": True}

    # Use all registered tools if none specified
    tool_names = tools or [t["name"] for t in get_all_tools()]
    audit_entries: list[dict] = []
    run_id_ref: list = []
    lc_tools = [_build_lc_tool(name, audit_entries, run_id_ref) for name in tool_names]

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

    # Write audit logs for every tool call
    if run_id and audit_entries:
        for entry in audit_entries:
            db.add(AuditLog(
                tenant_id=tenant_id,
                run_id=run_id,
                tool_name=entry["tool_name"],
                input_args=entry["input_args"],
                output=entry["output"],
                status=entry["status"],
                latency_ms=entry["latency_ms"],
            ))

    # Structured trace log
    steps = [trace_tool_call(e["tool_name"], e["latency_ms"], e["status"]) for e in audit_entries]
    log_run(
        run_id=run_id or uuid.uuid4(),
        tenant_id=tenant_id,
        model=model,
        prompt=prompt,
        steps=steps,
        total_latency_ms=latency_ms,
        total_cost_usd=cost_usd,
        cache_hit=False,
    )

    response = {
        "output": output,
        "tool_calls": tool_calls,
        "tokens_used": {"input": tokens_in, "output": tokens_out},
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "cache_hit": False,
    }

    # Cache the response for identical future prompts
    await set_cached(model, SYSTEM_PROMPT, prompt, response)

    return response
