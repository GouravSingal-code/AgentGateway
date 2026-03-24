"""Structured per-run logging."""
import hashlib
import uuid

import structlog

logger = structlog.get_logger()


def log_run(
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    model: str,
    prompt: str,
    steps: list[dict],
    total_latency_ms: int,
    total_cost_usd: float,
    cache_hit: bool = False,
) -> None:
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    logger.info(
        "run_trace",
        run_id=str(run_id),
        tenant_id=str(tenant_id),
        model=model,
        prompt_hash=prompt_hash,
        cache_hit=cache_hit,
        steps=steps,
        total_latency_ms=total_latency_ms,
        total_cost_usd=total_cost_usd,
    )


def trace_tool_call(tool: str, latency_ms: int, status: str) -> dict:
    return {"type": "tool_call", "tool": tool, "latency_ms": latency_ms, "status": status}


def trace_llm_call(tokens_in: int, tokens_out: int, latency_ms: int, cache_hit: bool = False) -> dict:
    return {
        "type": "llm_call",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "cache_hit": cache_hit,
    }
