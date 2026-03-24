"""Model routing logic: promotes cheaper model when quality stays within threshold."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalResult

# If cheaper model accuracy is within 5% and latency within 50% -> route there
ACCURACY_TOLERANCE = 0.05
LATENCY_TOLERANCE = 1.5
MIN_EVAL_RUNS = 10

CHEAPER_MODEL = "claude-haiku-4-5"
PRIMARY_MODEL = "claude-sonnet-4-6"


async def evaluate_routing(db: AsyncSession) -> dict:
    primary_stats = await _get_model_stats(db, PRIMARY_MODEL)
    cheaper_stats = await _get_model_stats(db, CHEAPER_MODEL)

    if not primary_stats or not cheaper_stats:
        return {"recommendation": PRIMARY_MODEL, "reason": "insufficient_eval_data"}

    accuracy_ok = cheaper_stats["avg_accuracy"] >= primary_stats["avg_accuracy"] - ACCURACY_TOLERANCE
    latency_ok = cheaper_stats["avg_latency_ms"] <= primary_stats["avg_latency_ms"] * LATENCY_TOLERANCE

    if accuracy_ok and latency_ok:
        return {
            "recommendation": CHEAPER_MODEL,
            "reason": "quality_within_threshold",
            "primary_accuracy": primary_stats["avg_accuracy"],
            "cheaper_accuracy": cheaper_stats["avg_accuracy"],
        }

    return {
        "recommendation": PRIMARY_MODEL,
        "reason": "cheaper_model_below_threshold",
        "primary_accuracy": primary_stats["avg_accuracy"],
        "cheaper_accuracy": cheaper_stats["avg_accuracy"],
    }


async def _get_model_stats(db: AsyncSession, model: str) -> dict | None:
    from app.db.models import AgentRun

    result = await db.execute(
        select(
            func.avg(EvalResult.accuracy_score).label("avg_accuracy"),
            func.avg(AgentRun.latency_ms).label("avg_latency_ms"),
            func.count(EvalResult.id).label("count"),
        )
        .join(AgentRun, EvalResult.run_id == AgentRun.id)
        .where(AgentRun.model == model)
    )
    row = result.one_or_none()
    if not row or row.count < MIN_EVAL_RUNS:
        return None
    return {"avg_accuracy": float(row.avg_accuracy or 0), "avg_latency_ms": float(row.avg_latency_ms or 0)}
