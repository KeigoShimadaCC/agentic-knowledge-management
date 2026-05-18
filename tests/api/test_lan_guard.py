"""LAN-allowlist middleware unit tests (PHASE-FIX-04 / S5)."""

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
