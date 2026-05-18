"""LAN-allowlist middleware unit tests (PHASE-FIX-04 / S5)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.lan_guard import install_lan_guard


def _make_app(*, trusted_proxy_count: int = 0) -> FastAPI:
    app = FastAPI()
    install_lan_guard(app, trusted_proxy_count=trusted_proxy_count)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_loopback_client_is_allowed():
    app = _make_app()
    transport = ASGITransport(app=app, client=("127.0.0.1", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_private_lan_client_is_allowed():
    app = _make_app()
    transport = ASGITransport(app=app, client=("192.168.1.42", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_client_is_rejected():
    app = _make_app()
    transport = ASGITransport(app=app, client=("8.8.8.8", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe")
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "lan_guard"


@pytest.mark.asyncio
async def test_xff_ignored_when_trusted_proxy_count_zero():
    """With trusted_proxy_count=0, a forged XFF must not bypass the guard."""
    app = _make_app(trusted_proxy_count=0)
    transport = ASGITransport(app=app, client=("8.8.8.8", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe", headers={"X-Forwarded-For": "127.0.0.1"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_xff_honored_when_trusted_proxy_count_one():
    """With trusted_proxy_count=1, the rightmost XFF entry is the trusted client."""
    app = _make_app(trusted_proxy_count=1)
    transport = ASGITransport(app=app, client=("8.8.8.8", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe", headers={"X-Forwarded-For": "10.0.0.5"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_xff_rejected_when_rightmost_is_public():
    app = _make_app(trusted_proxy_count=1)
    transport = ASGITransport(app=app, client=("10.0.0.1", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/probe", headers={"X-Forwarded-For": "8.8.8.8"})
    assert resp.status_code == 403


def test_mobile_compose_keeps_both_safety_env_vars():
    """The mobile compose layer must keep KOS_PROFILE + ALLOW_OPEN_REGISTRATION in lockstep.

    Both layers (S5 layer 1: open-reg off; layer 2: LAN guard) are required for the
    mobile profile's threat model. A future edit that drops either should fail this
    test before merge.
    """
    path = (
        Path(__file__).resolve().parents[2] / "infra" / "docker-compose.mobile.yml"
    )
    content = path.read_text()
    assert "KOS_PROFILE: mobile" in content, "mobile profile must activate LAN guard"
    assert 'ALLOW_OPEN_REGISTRATION: "false"' in content, (
        "mobile profile must disable open registration"
    )


@pytest.mark.asyncio
async def test_register_returns_403_when_open_registration_disabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Combined layer-1 mobile-profile assertion: with ALLOW_OPEN_REGISTRATION=false,
    POST /auth/register is refused even from an authenticated-looking client.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "allow_open_registration", False)
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "guest@example.com",
            "password": "password123",
            "display_name": "Guest",
        },
    )
    assert resp.status_code == 403
