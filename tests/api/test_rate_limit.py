"""Unit tests for the Redis sliding-window rate limiter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.rate_limit import RateLimitError, agent_id_from_request, check_and_increment


def _make_redis(minute_count: int = 0, hour_count: int = 0) -> MagicMock:
    """Return a mock Redis whose pipeline reports the given bucket sizes."""
    redis = MagicMock()

    # Each call to redis.pipeline() returns a new pipeline mock.
    # check_and_increment calls pipeline() 3 times total:
    #   1st: minute zremrangebyscore + zcard  → [0, minute_count]
    #   2nd: hour   zremrangebyscore + zcard  → [0, hour_count]
    #   3rd: record both buckets (zadd + expire x2) → not inspected
    call_count = 0

    def make_pipe():
        nonlocal call_count
        call_count += 1
        current_call = call_count

        pipe = MagicMock()
        pipe.zremrangebyscore = MagicMock(return_value=pipe)
        pipe.zcard = MagicMock(return_value=pipe)
        pipe.zadd = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)

        if current_call == 1:
            pipe.execute = AsyncMock(return_value=[0, minute_count])
        elif current_call == 2:
            pipe.execute = AsyncMock(return_value=[0, hour_count])
        else:
            pipe.execute = AsyncMock(return_value=[])

        return pipe

    redis.pipeline = MagicMock(side_effect=make_pipe)
    return redis


@pytest.mark.asyncio
async def test_allow_within_minute_limit():
    """Calls below the per-minute limit are allowed."""
    redis = _make_redis(minute_count=59, hour_count=0)
    result = await check_and_increment("agent-abc", redis)
    assert result is True


@pytest.mark.asyncio
async def test_deny_on_61st_call_in_minute():
    """The 61st call in a minute window raises RateLimitError."""
    redis = _make_redis(minute_count=60, hour_count=0)
    with pytest.raises(RateLimitError) as exc_info:
        await check_and_increment("agent-abc", redis)
    err = exc_info.value
    assert err.kind == "minute"
    assert err.limit == 60
    assert "60 writes per minute" in str(err)


@pytest.mark.asyncio
async def test_deny_on_601st_call_in_hour():
    """The 601st call in an hour window raises RateLimitError (hour bucket)."""
    redis = _make_redis(minute_count=0, hour_count=600)
    with pytest.raises(RateLimitError) as exc_info:
        await check_and_increment("agent-abc", redis)
    err = exc_info.value
    assert err.kind == "hour"
    assert err.limit == 600
    assert "600 writes per hour" in str(err)


@pytest.mark.asyncio
async def test_missing_agent_id_uses_shared_bucket():
    """Requests without X-KOS-Agent-Id fall back to a shared bucket keyed by token hash."""
    mock_request = MagicMock()
    mock_request.headers = {}

    with patch("app.core.rate_limit.settings") as mock_settings:
        mock_settings.mcp_agent_id_header = "X-KOS-Agent-Id"
        mock_settings.mcp_internal_token = "secret-token"
        agent_id = agent_id_from_request(mock_request)

    assert agent_id.startswith("shared:")
    assert len(agent_id) > len("shared:")


@pytest.mark.asyncio
async def test_explicit_agent_id_header_used():
    """X-KOS-Agent-Id header is used as-is for the rate-limit bucket."""
    mock_request = MagicMock()
    mock_request.headers = {"X-KOS-Agent-Id": "claude-desktop-session-42"}

    with patch("app.core.rate_limit.settings") as mock_settings:
        mock_settings.mcp_agent_id_header = "X-KOS-Agent-Id"
        agent_id = agent_id_from_request(mock_request)

    assert agent_id == "claude-desktop-session-42"
