import time

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException, Request, status

from app.config import settings

logger = structlog.get_logger()
_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(request: Request) -> None:
    tenant = getattr(request.state, "tenant", None)
    if tenant is None:
        return

    redis = get_redis()
    window = int(time.time() // 60)
    key = f"rate:{tenant.id}:{window}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)

    if current > tenant.rate_limit_rpm:
        logger.warning("rate_limit_exceeded", tenant=tenant.name, count=current)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {tenant.rate_limit_rpm} requests/min",
        )
