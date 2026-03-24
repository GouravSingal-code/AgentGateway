"""Eval harness: loads YAML test cases, runs agent, scores results."""
import uuid
from pathlib import Path
from typing import Any

import yaml
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.executor import run_agent
from app.db.models import AgentRun, EvalResult
from app.eval.scorer import combined_score, score_output, score_tool_calls

logger = structlog.get_logger()
CASES_DIR = Path(__file__).parent / "test_cases"


def load_suite(suite: str) -> list[dict]:
    path = CASES_DIR / f"{suite}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Test suite not found: {suite}")
    with path.open() as f:
        return yaml.safe_load(f)


async def run_eval_suite(
    suite: str,
    models: list[str],
    runs_per_case: int,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    cases = load_suite(suite)
    model_results: dict[str, list] = {m: [] for m in models}

    for model in models:
        for case in cases:
            for _ in range(runs_per_case):
                try:
                    result = await run_agent(
                        prompt=case["prompt"],
                        tools=case.get("expected_tool_calls", []),
                        model=model,
                        max_steps=10,
                        tenant_id=tenant_id,
                        db=db,
                    )

                    output_score = score_output(result["output"], case.get("expected_output_contains", []))
                    tool_score = score_tool_calls(result["tool_calls"], case.get("expected_tool_calls", []))
                    accuracy = combined_score(output_score, tool_score)

                    run_record = AgentRun(
                        tenant_id=tenant_id,
                        prompt=case["prompt"],
                        model=model,
                        output=result["output"],
                        tool_calls=result["tool_calls"],
                        tokens_input=result["tokens_used"]["input"],
                        tokens_output=result["tokens_used"]["output"],
                        cost_usd=result["cost_usd"],
                        latency_ms=result["latency_ms"],
                        status="success",
                    )
                    db.add(run_record)
                    await db.flush()

                    eval_result = EvalResult(
                        run_id=run_record.id,
                        suite_name=suite,
                        test_case_id=case["id"],
                        model=model,
                        accuracy_score=accuracy,
                    )
                    db.add(eval_result)
                    model_results[model].append(
                        {"accuracy": accuracy, "cost_usd": result["cost_usd"], "latency_ms": result["latency_ms"]}
                    )
                except Exception as e:
                    logger.error("eval_case_failed", case=case["id"], model=model, error=str(e))

        await db.commit()

    return _summarize(model_results)


def _summarize(model_results: dict[str, list]) -> list[dict]:
    summary = []
    for model, runs in model_results.items():
        if not runs:
            continue
        avg_accuracy = sum(r["accuracy"] for r in runs) / len(runs)
        avg_cost = sum(r["cost_usd"] for r in runs) / len(runs)
        avg_latency = sum(r["latency_ms"] for r in runs) / len(runs)
        summary.append(
            {
                "model": model,
                "avg_accuracy": round(avg_accuracy, 4),
                "avg_cost_usd": round(avg_cost, 6),
                "avg_latency_ms": round(avg_latency, 1),
                "recommendation": "route_here" if avg_accuracy >= 0.85 else "needs_improvement",
            }
        )
    return sorted(summary, key=lambda x: x["avg_cost_usd"])
