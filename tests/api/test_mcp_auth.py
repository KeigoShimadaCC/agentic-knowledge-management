import uuid

import pytest
from httpx import AsyncClient


async def _register_user(client: AsyncClient) -> None:
    email = f"mcp-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "MCP User"},
    )


@pytest.mark.asyncio
async def test_valid_token_grants_access(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.config import settings

    await _register_user(client)
    monkeypatch.setattr(settings, "mcp_internal_token", "test-mcp-token-abc123")

    resp = await client.get(
        "/api/v1/objects",
        headers={"X-KOS-Internal-Token": "test-mcp-token-abc123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_invalid_token_falls_through_to_cookie_auth(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    await _register_user(client)
    monkeypatch.setattr(settings, "mcp_internal_token", "correct-token")

    # Clear cookie so only the token is checked; wrong token → 401
    client.cookies.clear()
    resp = await client.get(
        "/api/v1/objects",
        headers={"X-KOS-Internal-Token": "wrong-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scoped_user_id_resolves_to_that_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select

    await _register_user(client)
    await _register_user(client)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.deleted_at.is_(None)).order_by(User.created_at)
        )
        users = list(result.scalars().all())
    assert len(users) >= 2
    scoped_uid = str(users[1].id)

    monkeypatch.setattr(settings, "mcp_internal_token", "scoped-token-xyz")
    monkeypatch.setattr(settings, "mcp_internal_user_id", scoped_uid)
    client.cookies.clear()

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"X-KOS-Internal-Token": "scoped-token-xyz"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["id"] == scoped_uid


@pytest.mark.asyncio
async def test_scoped_user_id_rejects_invalid_uuid(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    await _register_user(client)
    monkeypatch.setattr(settings, "mcp_internal_token", "scoped-token-bad")
    monkeypatch.setattr(settings, "mcp_internal_user_id", "not-a-uuid")
    client.cookies.clear()

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"X-KOS-Internal-Token": "scoped-token-bad"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_token_config_ignores_header(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    await _register_user(client)
    # Token is empty in config — any header value must be ignored; clear cookie so only
    # the token path is tested
    monkeypatch.setattr(settings, "mcp_internal_token", "")
    client.cookies.clear()

    resp = await client.get(
        "/api/v1/objects",
        headers={"X-KOS-Internal-Token": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_token_header_falls_through_to_cookie(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "mcp_internal_token", "some-token")

    # No header, no cookie → 401
    resp = await client.get("/api/v1/objects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_auth_requires_existing_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    # No registered user — token path finds no active user, falls through to cookie → 401
    monkeypatch.setattr(settings, "mcp_internal_token", "test-token")

    resp = await client.get(
        "/api/v1/objects",
        headers={"X-KOS-Internal-Token": "test-token"},
    )
    assert resp.status_code == 401
