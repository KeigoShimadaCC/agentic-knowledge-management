import json
from datetime import datetime, timedelta, timezone

import pytest
from app.core.security import hash_token
from app.db.session import engine
from app.models.session import Session
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _register(
    client: AsyncClient,
    *,
    email: str = "mobile@test.com",
    password: str = "password123",
    display_name: str = "Mobile User",
) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert resp.status_code == 201, resp.text


async def _mobile_login(
    client: AsyncClient,
    *,
    email: str = "mobile@test.com",
    password: str = "password123",
    device_name: str | None = "Demo iPhone",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/mobile-login",
        json={"email": email, "password": password, "device_name": device_name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_mobile_login_returns_token_once_and_stores_only_hash(client: AsyncClient):
    await _register(client)
    client.cookies.clear()

    data = await _mobile_login(client)
    token = data["token"]

    assert data["user"]["email"] == "mobile@test.com"
    assert token
    assert "expires_at" in data

    async with AsyncSession(engine) as db:
        result = await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
        session = result.scalar_one()

    assert session.client_type == "ios"
    assert session.device_name == "Demo iPhone"
    assert session.token_hash != token


@pytest.mark.asyncio
async def test_mobile_login_wrong_password_returns_401(client: AsyncClient):
    await _register(client)
    client.cookies.clear()

    resp = await client.post(
        "/api/v1/auth/mobile-login",
        json={"email": "mobile@test.com", "password": "wrongpassword"},
    )

    assert resp.status_code == 401
    assert "token" not in resp.text


@pytest.mark.asyncio
async def test_mobile_login_missing_email_returns_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/mobile-login",
        json={"password": "password123", "device_name": "Phone"},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bearer_token_authenticates_auth_me(client: AsyncClient):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "mobile@test.com"


@pytest.mark.asyncio
async def test_authenticated_request_updates_last_seen(client: AsyncClient):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]
    old_seen = datetime.now(timezone.utc) - timedelta(days=1)

    async with AsyncSession(engine) as db:
        result = await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
        session = result.scalar_one()
        session.last_seen = old_seen
        await db.commit()

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    async with AsyncSession(engine) as db:
        result = await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
        session = result.scalar_one()

    assert session.last_seen > old_seen


@pytest.mark.asyncio
async def test_mobile_logout_revokes_bearer_token(client: AsyncClient):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout = await client.post("/api/v1/auth/mobile-logout", headers=headers)
    assert logout.status_code == 200

    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthenticated"


@pytest.mark.asyncio
async def test_mobile_bootstrap_returns_boolean_capabilities(client: AsyncClient):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]

    resp = await client.get(
        "/api/v1/mobile/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "mobile@test.com"
    assert data["capabilities"] == {
        "ai_enabled": True,
        "embeddings_enabled": True,
        "upload_enabled": True,
        "mobile_api_version": 1,
    }


@pytest.mark.asyncio
async def test_token_never_appears_in_response_bodies_after_creation(client: AsyncClient):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    bootstrap = await client.get("/api/v1/mobile/bootstrap", headers=headers)

    assert token not in json.dumps(me.json())
    assert token not in json.dumps(bootstrap.json())


@pytest.mark.asyncio
async def test_token_never_appears_in_logs(client: AsyncClient, caplog: pytest.LogCaptureFixture):
    await _register(client)
    client.cookies.clear()
    token = (await _mobile_login(client))["token"]

    await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert token not in caplog.text


@pytest.mark.asyncio
async def test_other_user_access_with_bearer_returns_404(client: AsyncClient):
    await _register(client, email="owner@test.com", display_name="Owner")
    owner_page = await client.post("/api/v1/pages", json={"title": "Private Page"})
    assert owner_page.status_code == 201
    page_id = owner_page.json()["page"]["id"]

    client.cookies.clear()
    await _register(client, email="other@test.com", display_name="Other")
    client.cookies.clear()
    token = (await _mobile_login(client, email="other@test.com", device_name="Other Phone"))[
        "token"
    ]

    resp = await client.get(
        f"/api/v1/pages/{page_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404
