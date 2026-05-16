import os
import json
from cryptography.fernet import Fernet

if 'MCP_ENV_ENCRYPTION_KEY' not in os.environ:
    os.environ['MCP_ENV_ENCRYPTION_KEY'] = Fernet.generate_key().decode()

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.mcp_connection import McpConnection
from sqlalchemy import select


pytestmark = pytest.mark.asyncio

BASE_URL = "/api/v1/mcp-connections"


def make_fake_proc():
    proc = MagicMock()
    proc.returncode = None
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    initialize_resp = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": "2024-11-05", "capabilities": {}},
            }
        ).encode()
        + b"\n"
    )
    tools_resp = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search the web",
                            "inputSchema": {},
                        }
                    ]
                },
            }
        ).encode()
        + b"\n"
    )
    proc.stdout = MagicMock()
    proc.stdout.readline = AsyncMock(side_effect=[initialize_resp, tools_resp])
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


async def create_connection(auth_client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": "Example MCP",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-example"],
    }
    payload.update(overrides)
    resp = await auth_client.post(f"{BASE_URL}/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_stdio_connection_returns_201(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"{BASE_URL}/",
        json={
            "name": "Stdio MCP",
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-example"],
            "env_vars": {"API_KEY": "secret"},
        },
    )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"]
    assert data["transport"] == "stdio"
    assert data["env_vars"] == {"API_KEY": "*****"}


async def test_create_sse_connection_returns_201(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"{BASE_URL}/",
        json={
            "name": "SSE MCP",
            "transport": "sse",
            "url": "http://localhost:9000/mcp",
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["transport"] == "sse"


async def test_create_stdio_missing_command_returns_400(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"{BASE_URL}/",
        json={"name": "Missing Command", "transport": "stdio"},
    )

    assert resp.status_code == 400


async def test_create_sse_missing_url_returns_400(auth_client: AsyncClient):
    resp = await auth_client.post(
        f"{BASE_URL}/",
        json={"name": "Missing URL", "transport": "sse"},
    )

    assert resp.status_code == 400


async def test_get_connection_env_vars_redacted(auth_client: AsyncClient):
    created = await create_connection(
        auth_client,
        name="Secret MCP",
        env_vars={"API_KEY": "secret", "TOKEN": "plaintext"},
    )

    resp = await auth_client.get(f"{BASE_URL}/{created['id']}")

    assert resp.status_code == 200, resp.text
    assert resp.json()["env_vars"] == {"API_KEY": "*****", "TOKEN": "*****"}


async def test_list_connections_excludes_deleted(auth_client: AsyncClient):
    keep = await create_connection(auth_client, name="Keep MCP")
    delete = await create_connection(auth_client, name="Delete MCP")

    delete_resp = await auth_client.delete(f"{BASE_URL}/{delete['id']}")
    assert delete_resp.status_code == 204

    resp = await auth_client.get(f"{BASE_URL}/")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == keep["id"]


async def test_patch_connection_updates_name(auth_client: AsyncClient):
    created = await create_connection(auth_client, name="Before")

    patch_resp = await auth_client.patch(f"{BASE_URL}/{created['id']}", json={"name": "Updated"})
    get_resp = await auth_client.get(f"{BASE_URL}/{created['id']}")

    assert patch_resp.status_code == 200, patch_resp.text
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["name"] == "Updated"


async def test_delete_connection_returns_204(auth_client: AsyncClient):
    created = await create_connection(auth_client)

    resp = await auth_client.delete(f"{BASE_URL}/{created['id']}")

    assert resp.status_code == 204


async def test_other_user_cannot_get_connection(auth_client: AsyncClient):
    created = await create_connection(auth_client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as user_b:
        register_resp = await user_b.post(
            "/api/v1/auth/register",
            json={
                "email": "b@test.com",
                "password": "password123",
                "display_name": "User B",
            },
        )
        assert register_resp.status_code == 201, register_resp.text
        resp = await user_b.get(f"{BASE_URL}/{created['id']}")

    assert resp.status_code in (401, 404)


async def test_env_vars_encrypted_in_db(auth_client: AsyncClient):
    created = await create_connection(
        auth_client,
        name="Encrypted MCP",
        env_vars={"SECRET": "plaintext"},
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(McpConnection).where(McpConnection.id == created["id"])
        )
        conn = result.scalar_one()

    assert conn.env_vars["SECRET"] != "plaintext"


async def test_test_connection_success(auth_client: AsyncClient):
    created = await create_connection(auth_client, name="Runnable MCP")

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=make_fake_proc()),
    ):
        resp = await auth_client.post(f"{BASE_URL}/{created['id']}/test")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "search"


async def test_test_connection_timeout_returns_422(auth_client: AsyncClient):
    created = await create_connection(auth_client, name="Timeout MCP")
    proc = make_fake_proc()
    proc.stdout.readline = AsyncMock(side_effect=TimeoutError)

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
        resp = await auth_client.post(f"{BASE_URL}/{created['id']}/test")

    assert resp.status_code == 422

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(McpConnection).where(McpConnection.id == created["id"])
        )
        conn = result.scalar_one()

    assert conn.last_error == "timeout after 10s"


async def test_create_with_no_encryption_key_returns_400(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "mcp_env_encryption_key", "")

    resp = await auth_client.post(
        f"{BASE_URL}/",
        json={
            "name": "No Encryption MCP",
            "transport": "stdio",
            "command": "uvx",
            "env_vars": {"API_KEY": "secret"},
        },
    )

    assert resp.status_code == 400
