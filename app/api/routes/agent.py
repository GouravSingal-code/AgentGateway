import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.executor import run_agent
from app.api.middleware.rate_limit import check_rate_limit
from app.db.models import AgentRun
from app.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/run", tags=["agent"])


class RunRequest(BaseModel):
    prompt: str
    tools: List[str] = []
    model: str = "claude-sonnet-4-6"
    max_steps: int = 10


class RunResponse(BaseModel):
    run_id: uuid.UUID
    output: str
    tool_calls: list
    tokens_used: dict
    cost_usd: float
    latency_ms: int


@router.post("", response_model=RunResponse)
async def run(
    body: RunRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit),
):
    tenant = request.state.tenant

    result = await run_agent(
        prompt=body.prompt,
        tools=body.tools,
        model=body.model,
        max_steps=body.max_steps,
        tenant_id=tenant.id,
        db=db,
    )

    run_record = AgentRun(
        tenant_id=tenant.id,
        prompt=body.prompt,
        model=body.model,
        output=result["output"],
        tool_calls=result["tool_calls"],
        tokens_input=result["tokens_used"]["input"],
        tokens_output=result["tokens_used"]["output"],
        cost_usd=result["cost_usd"],
        latency_ms=result["latency_ms"],
        status="success",
    )
    db.add(run_record)
    await db.commit()
    await db.refresh(run_record)

    logger.info(
        "agent_run_complete",
        run_id=str(run_record.id),
        model=body.model,
        cost_usd=result["cost_usd"],
        latency_ms=result["latency_ms"],
    )

    return RunResponse(
        run_id=run_record.id,
        output=result["output"],
        tool_calls=result["tool_calls"],
        tokens_used=result["tokens_used"],
        cost_usd=result["cost_usd"],
        latency_ms=result["latency_ms"],
    )
