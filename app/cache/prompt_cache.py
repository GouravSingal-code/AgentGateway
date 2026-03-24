"""Redis-backed prompt response cache keyed by SHA256 of (model + prompt prefix)."""
import hashlib
import json

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _cache_key(model: str, system_prompt: str, user_prompt: str) -> str:
    raw = f"{model}::{system_prompt[:500]}::{user_prompt[:500]}"
    return "prompt_cache:" + hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(model: str, system_prompt: str, user_prompt: str) -> dict | None:
    key = _cache_key(model, system_prompt, user_prompt)
    value = await _get_redis().get(key)
    if value:
        return json.loads(value)
    return None


async def set_cached(model: str, system_prompt: str, user_prompt: str, response: dict) -> None:
    key = _cache_key(model, system_prompt, user_prompt)
    await _get_redis().setex(key, settings.prompt_cache_ttl, json.dumps(response))
