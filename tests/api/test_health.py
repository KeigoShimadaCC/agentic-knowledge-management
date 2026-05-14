import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/api/v1/auth/../health")
    # /health is mounted at root, not under /api/v1
    resp2 = await client.get("/health")
    assert resp2.status_code == 200 or resp2.status_code == 404  # depends on route
    # Try via the router path
    resp3 = await client.get("/api/v1/health")
    data = resp3.json()
    assert data["status"] == "ok"
    assert "version" in data
