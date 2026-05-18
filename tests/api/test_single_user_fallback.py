"""Single-user no-auth fallback for the desktop profile.

Desktop profile (default) binds to 127.0.0.1 only, so an authenticated session is
not required; `get_current_user` returns the first non-deleted user when no
bearer / cookie / MCP token resolves. Mobile profile must still require auth — the
LAN guard in `app/middleware/lan_guard.py` does NOT compensate for missing user auth.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_desktop_profile_no_auth_returns_local_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """With no bearer, no cookie, no MCP token, desktop returns the local user."""
    from app.config import settings

    monkeypatch.setattr(settings, "kos_profile", "desktop")
    # Register one user so the fallback has someone to return.
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "local@example.com",
            "password": "password123",
            "display_name": "Local",
        },
    )
    assert register.status_code == 201, register.text
    client.cookies.clear()

    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["email"] == "local@example.com"


@pytest.mark.asyncio
async def test_mobile_profile_no_auth_returns_401(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Mobile profile (LAN-exposed) keeps requiring real auth."""
    from app.config import settings

    monkeypatch.setattr(settings, "kos_profile", "mobile")
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "guarded@example.com",
            "password": "password123",
            "display_name": "Guarded",
        },
    )
    assert register.status_code == 201, register.text
    client.cookies.clear()

    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_desktop_profile_no_user_in_db_returns_401(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Fallback returns 401 when there is no user at all (e.g., empty test DB)."""
    from app.config import settings

    monkeypatch.setattr(settings, "kos_profile", "desktop")
    client.cookies.clear()

    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_invalid_bearer_still_401_in_desktop_profile(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """An explicitly-sent invalid bearer must short-circuit to 401; the fallback
    only fires when NO auth is attempted, not when auth is attempted and fails.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "kos_profile", "desktop")
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "password123",
            "display_name": "Owner",
        },
    )
    assert register.status_code == 201, register.text
    client.cookies.clear()

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_ensure_local_user_creates_demo_when_db_empty():
    """ensure_local_user creates the demo user when no users exist."""
    from app.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from app.services import demo_seed_service
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.deleted_at.is_(None)))
        assert existing.scalars().first() is None

        user = await demo_seed_service.ensure_local_user(db)
        await db.commit()

    assert user.email == settings.demo_seed_email


@pytest.mark.asyncio
async def test_ensure_local_user_is_idempotent_with_existing_user():
    """ensure_local_user does not create a second user when one already exists."""
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from app.services import demo_seed_service
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        db.add(
            User(
                email="already-there@example.com",
                display_name="Already There",
                password_hash="x" * 60,
            )
        )
        await db.flush()
        await db.commit()

    async with AsyncSessionLocal() as db:
        await demo_seed_service.ensure_local_user(db)
        await db.commit()

    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(User.id)))).scalar_one()
    assert count == 1
