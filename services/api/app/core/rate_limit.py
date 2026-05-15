"""Redis-backed sliding-window rate limiter for MCP write tools."""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import Request
    from redis.asyncio import Redis

from app.config import settings

_WINDOWS: dict[str, int] = {"minute": 60, "hour": 3600}


class RateLimitError(Exception):
    """Raised when a per-agent rate limit is exceeded."""

    def __init__(self, kind: Literal["minute", "hour"], limit: int, retry_after: int) -> None:
        self.kind = kind
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} writes per {kind}. "
            f"Retry after {retry_after} seconds."
        )


async def check_and_increment(agent_id: str, redis: "Redis") -> bool:
    """Return True if the write is allowed; raise RateLimitError if either bucket is full.

    Both the per-minute and per-hour sliding windows must pass before the call is
    recorded. If either is exceeded no entry is written to Redis.
    """
    now = time.time()

    # Check both windows before recording anything
    for kind in ("minute", "hour"):
        window = _WINDOWS[kind]
        limit = (
            settings.mcp_rate_limit_per_minute
            if kind == "minute"
            else settings.mcp_rate_limit_per_hour
        )
        key = f"kos:rl:{kind}:{agent_id}"

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        results = await pipe.execute()
        count: int = results[1]

        if count >= limit:
            raise RateLimitError(kind=kind, limit=limit, retry_after=window)  # type: ignore[arg-type]

    # Both windows passed — record the call in both buckets
    pipe = redis.pipeline()
    member = str(uuid.uuid4())
    for kind in ("minute", "hour"):
        window = _WINDOWS[kind]
        key = f"kos:rl:{kind}:{agent_id}"
        pipe.zadd(key, {member: now})
        pipe.expire(key, window)
    await pipe.execute()

    return True


def agent_id_from_request(request: "Request") -> str:
    """Derive a stable rate-limit identity from the request.

    Uses X-KOS-Agent-Id if present; falls back to a hash of the internal token
    so all unidentified MCP callers share one bucket.
    """
    agent_id = request.headers.get(settings.mcp_agent_id_header, "")
    if not agent_id:
        token = settings.mcp_internal_token or "anonymous"
        agent_id = "shared:" + hashlib.sha256(token.encode()).hexdigest()[:16]
    return agent_id


async def get_redis():
    """FastAPI dependency: async Redis client."""
    import redis.asyncio as aioredis

    r: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()
