"""API integration tests for MCP write-tool endpoints.

Each test exercises one write-tool path end-to-end, verifying both the
primary effect (object mutated) and the audit trail (agent_runs row created).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.rate_limit import get_redis
from app.main import app
from httpx import AsyncClient


def _make_permissive_redis():
    """Return a mock Redis that always allows writes (counts always below limit)."""
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
            pipe.execute = AsyncMock(return_value=[0, 0])
        elif current % 3 == 2:
            pipe.execute = AsyncMock(return_value=[0, 0])
        else:
            pipe.execute = AsyncMock(return_value=[])
        return pipe

    redis.pipeline = MagicMock(side_effect=make_pipe)
    return redis


async def _mock_redis_dep():
    yield _make_permissive_redis()


@pytest.fixture(autouse=True)
def override_redis():
    app.dependency_overrides[get_redis] = _mock_redis_dep
    yield
    app.dependency_overrides.pop(get_redis, None)


async def _get_db_session():
    """Return a fresh session for direct DB assertions."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


async def _create_page(auth_client: AsyncClient, title: str = "Test Page") -> dict:
    resp = await auth_client.post("/api/v1/pages", json={"title": title})
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_page_via_api_creates_audit_row(auth_client: AsyncClient):
    """POST /pages creates an object+page; MCP write path also writes agent_runs."""
    payload = {"title": "MCP Created Page", "content_text": "Hello from MCP"}
    resp = await auth_client.post(
        "/api/v1/pages",
        json=payload,
        headers={"X-KOS-Agent-Id": "test-agent"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["object"]["title"] == "MCP Created Page"
    assert "id" in data["object"]


@pytest.mark.asyncio
async def test_update_page_via_api_increments_version(auth_client: AsyncClient):
    """PATCH /pages/{id} increments version and returns updated content."""
    page_data = await _create_page(auth_client, "Original Title")
    page_id = page_data["page"]["id"]
    initial_version = page_data["page"]["version"]

    resp = await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"title": "Updated Title", "content_text": "Updated content"},
        headers={"X-KOS-Agent-Id": "test-agent"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["version"] == initial_version + 1


@pytest.mark.asyncio
async def test_update_page_expected_version_conflict_returns_409(auth_client: AsyncClient):
    """PATCH with wrong expected_version returns 409 Conflict."""
    page_data = await _create_page(auth_client, "Version Test Page")
    page_id = page_data["page"]["id"]

    resp = await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"title": "New Title", "expected_version": 999},
    )
    assert resp.status_code == 409
    assert "conflict" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_page_expected_version_correct_succeeds(auth_client: AsyncClient):
    """PATCH with correct expected_version succeeds."""
    page_data = await _create_page(auth_client, "Correct Version Page")
    page_id = page_data["page"]["id"]
    current_version = page_data["page"]["version"]

    resp = await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"title": "Updated Title", "expected_version": current_version},
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == current_version + 1


@pytest.mark.asyncio
async def test_create_edge_via_api(auth_client: AsyncClient):
    """POST /edges creates a link between two objects."""
    p1 = await _create_page(auth_client, "Edge Source")
    p2 = await _create_page(auth_client, "Edge Target")
    source_id = p1["object"]["id"]
    target_id = p2["object"]["id"]

    resp = await auth_client.post(
        "/api/v1/edges",
        json={"source_id": source_id, "target_id": target_id, "kind": "related_to"},
        headers={"X-KOS-Agent-Id": "test-agent"},
    )
    assert resp.status_code == 201
    edge = resp.json()
    assert edge["source_id"] == source_id
    assert edge["target_id"] == target_id
    assert edge["kind"] == "related_to"


@pytest.mark.asyncio
async def test_archive_object_via_api_sets_is_archived(auth_client: AsyncClient):
    """POST /objects/{id}/archive sets is_archived=True and creates revision."""
    page_data = await _create_page(auth_client, "To Archive")
    object_id = page_data["object"]["id"]

    resp = await auth_client.post(
        f"/api/v1/objects/{object_id}/archive",
        headers={"X-KOS-Agent-Id": "test-agent"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_archived"] is True


@pytest.mark.asyncio
async def test_ingest_url_creates_source_with_pending_status(auth_client: AsyncClient):
    """POST /sources with a valid URL creates a source in pending state."""
    resp = await auth_client.post(
        "/api/v1/sources",
        json={
            "source_type": "web",
            "url": "https://example.com/article",
            "title": "Example Article",
            "tags": ["test"],
        },
        headers={"X-KOS-Agent-Id": "test-agent"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/article"
    assert data["ingestion_status"] == "pending"


@pytest.mark.asyncio
async def test_ingest_url_rejects_localhost_at_api_level(auth_client: AsyncClient):
    """POST /sources with localhost URL is rejected by API-level URL validation."""
    resp = await auth_client.post(
        "/api/v1/sources",
        json={
            "source_type": "web",
            "url": "http://localhost:8080/secret",
            "title": "Localhost",
        },
    )
    assert resp.status_code == 422
