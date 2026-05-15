"""Tests for POST /objects/{id}/archive and POST /objects/{id}/revisions/{rev_id}/restore."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.rate_limit import get_redis
from app.main import app
from httpx import AsyncClient


def _make_permissive_redis():
    """Return a mock Redis that always allows writes."""
    redis = MagicMock()

    call_count = 0

    def make_pipe():
        nonlocal call_count
        call_count += 1
        current = call_count

        pipe = MagicMock()
        pipe.zremrangebyscore = MagicMock(return_value=pipe)
        pipe.zcard = MagicMock(return_value=pipe)
        pipe.zadd = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)

        if current % 3 == 1:
            pipe.execute = AsyncMock(return_value=[0, 0])  # minute check
        elif current % 3 == 2:
            pipe.execute = AsyncMock(return_value=[0, 0])  # hour check
        else:
            pipe.execute = AsyncMock(return_value=[])  # record
        return pipe

    redis.pipeline = MagicMock(side_effect=make_pipe)
    return redis


async def _mock_redis_dep():
    yield _make_permissive_redis()


async def _create_page(auth_client: AsyncClient, title: str = "Test Page") -> dict:
    resp = await auth_client.post("/api/v1/pages", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture(autouse=True)
def override_redis():
    app.dependency_overrides[get_redis] = _mock_redis_dep
    yield
    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_archive_sets_is_archived_and_creates_revision(auth_client: AsyncClient):
    """POST /objects/{id}/archive flips is_archived=True."""
    page = await _create_page(auth_client, "Archive Me")
    object_id = page["object"]["id"]

    resp = await auth_client.post(f"/api/v1/objects/{object_id}/archive")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_archived"] is True
    assert data["id"] == object_id


@pytest.mark.asyncio
async def test_archive_is_idempotent(auth_client: AsyncClient):
    """Archiving an already-archived object returns 200 without error."""
    page = await _create_page(auth_client, "Double Archive")
    object_id = page["object"]["id"]

    resp1 = await auth_client.post(f"/api/v1/objects/{object_id}/archive")
    assert resp1.status_code == 200
    resp2 = await auth_client.post(f"/api/v1/objects/{object_id}/archive")
    assert resp2.status_code == 200
    assert resp2.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_restore_revision_rejects_wrong_object_id(auth_client: AsyncClient):
    """Restore endpoint returns 404 when revision does not belong to the given object."""
    page = await _create_page(auth_client, "Page One")
    object_id = page["object"]["id"]

    fake_rev_id = "00000000-0000-0000-0000-000000000001"
    resp = await auth_client.post(
        f"/api/v1/objects/{object_id}/revisions/{fake_rev_id}/restore"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_archive_unknown_object_returns_404(auth_client: AsyncClient):
    """Archive endpoint returns 404 for unknown object_id."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await auth_client.post(f"/api/v1/objects/{fake_id}/archive")
    assert resp.status_code == 404
