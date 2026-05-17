import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "password123", "display_name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "newuser@test.com"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_sets_session_cookie(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "cookie@test.com", "password": "password123", "display_name": "Cookie User"},
    )
    assert resp.status_code == 201
    assert "kos_session" in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "password123", "display_name": "Dup"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unable to complete registration"


@pytest.mark.asyncio
async def test_register_disabled_returns_403(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.config import settings

    monkeypatch.setattr(settings, "allow_open_registration", False)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "closed@test.com", "password": "password123", "display_name": "Closed"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_session_cookie_uses_secure_when_configured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "cookie_secure", True)
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "securecookie@test.com",
            "password": "password123",
            "display_name": "Secure Cookie",
        },
    )
    assert resp.status_code == 201
    set_cookie = resp.headers.get("set-cookie", "")
    assert "secure" in set_cookie.lower()


@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "password": "password123", "display_name": "Login User"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "login@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@test.com", "password": "password123", "display_name": "Wrong"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_cookie_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthenticated"


@pytest.mark.asyncio
async def test_me_with_valid_cookie_returns_user(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "test@test.com"


@pytest.mark.asyncio
async def test_logout_clears_session(auth_client: AsyncClient):
    resp = await auth_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # After logout, me should return 401
    resp2 = await auth_client.get("/api/v1/auth/me")
    assert resp2.status_code == 401
    assert resp2.json()["code"] == "unauthenticated"
