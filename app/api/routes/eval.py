import uuid
from typing import List

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.rate_limit import check_rate_limit
from app.db.session import get_db
from app.eval.harness import run_eval_suite

logger = structlog.get_logger()
router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRequest(BaseModel):
    suite: str
    models: List[str] = ["claude-sonnet-4-6"]
    runs_per_case: int = 1


class ModelEvalResult(BaseModel):
    model: str
    avg_accuracy: float
    avg_cost_usd: float
    avg_latency_ms: float
    recommendation: str


class EvalResponse(BaseModel):
    results: List[ModelEvalResult]


@router.post("", response_model=EvalResponse)
async def run_eval(
    body: EvalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit),
):
    tenant = request.state.tenant
    results = await run_eval_suite(
        suite=body.suite,
        models=body.models,
        runs_per_case=body.runs_per_case,
        tenant_id=tenant.id,
        db=db,
    )
    logger.info("eval_complete", suite=body.suite, models=body.models)
    return EvalResponse(results=results)


@router.post("/route")
async def trigger_model_routing(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit),
):
    """Manually trigger model routing re-evaluation."""
    from app.agent.router import evaluate_routing
    recommendation = await evaluate_routing(db=db)
    return {"recommendation": recommendation}


@router.get("/audit")
async def get_audit_logs(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_rate_limit),
):
    from sqlalchemy import select
    from app.db.models import AuditLog

    tenant = request.state.tenant
    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant.id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    return {"page": page, "page_size": page_size, "logs": [
        {
            "id": str(log.id),
            "run_id": str(log.run_id),
            "tool_name": log.tool_name,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]}
