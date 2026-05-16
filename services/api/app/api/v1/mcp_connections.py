import asyncio
import json
import os
import uuid
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.redaction import redact_env_vars
from app.db.session import get_db
from app.mcp_client.crypto import decrypt_env_vars
from app.models.mcp_connection import McpConnection
from app.models.user import User
from app.schemas.mcp_connection import (
    McpConnectionCreate,
    McpConnectionOut,
    McpConnectionTestResult,
    McpConnectionTransport,
    McpConnectionUpdate,
    McpToolDefinition,
)
from app.services import mcp_connection_service

router = APIRouter()


def _to_out(conn: McpConnection) -> McpConnectionOut:
    caps = None
    if conn.capabilities is not None:
        caps = [McpToolDefinition(**c) for c in conn.capabilities]
    return McpConnectionOut(
        id=conn.id,
        name=conn.name,
        transport=McpConnectionTransport(conn.transport),
        command=conn.command,
        args=conn.args or [],
        url=conn.url,
        env_vars=redact_env_vars(conn.env_vars or {}),
        capabilities=caps,
        enabled=conn.enabled,
        last_tested_at=conn.last_tested_at,
        last_error=conn.last_error,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


async def _run_stdio_test(conn: McpConnection, db: AsyncSession) -> McpConnectionTestResult:
    proc: asyncio.subprocess.Process | None = None
    try:
        decrypted_env_vars = decrypt_env_vars(conn.env_vars or {})
        env = {
            key: value
            for key in ("PATH", "HOME", "TMPDIR", "TEMP", "TMP")
            if (value := os.environ.get(key)) is not None
        }
        env.update(decrypted_env_vars)

        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                conn.command,
                *(conn.args or []),
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=10,
        )
        if proc.stdin is None or proc.stdout is None:
            raise KeyError("stdio")

        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "kos-test", "version": "1.0"},
            },
        }
        proc.stdin.write(json.dumps(initialize_request).encode() + b"\n")
        await proc.stdin.drain()

        initialize_line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
        initialize_response = json.loads(initialize_line)
        if "error" in initialize_response:
            raise RuntimeError(str(initialize_response["error"]))

        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        proc.stdin.write(json.dumps(initialized_notification).encode() + b"\n")
        await proc.stdin.drain()

        tools_list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        proc.stdin.write(json.dumps(tools_list_request).encode() + b"\n")
        await proc.stdin.drain()

        tools_line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
        tools_response = json.loads(tools_line)
        result = tools_response.get("result", {})
        tools = result.get("tools", [])

        with suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()

        await mcp_connection_service.cache_capabilities(db, conn, tools)
        await db.commit()
        return McpConnectionTestResult(
            ok=True,
            tools=[
                McpToolDefinition(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
                for tool in tools
            ],
        )
    except asyncio.TimeoutError:
        error_str = "timeout after 10s"
    except (FileNotFoundError, ProcessLookupError):
        error_str = f"command not found: {conn.command}"
    except json.JSONDecodeError:
        error_str = "invalid JSON-RPC response from server"
    except KeyError:
        error_str = "unexpected response format"
    except Exception as exc:
        error_str = str(exc)

    if proc is not None and proc.returncode is None:
        with suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()

    await mcp_connection_service.record_test_error(db, conn, error_str)
    await db.commit()
    raise HTTPException(status_code=422, detail=error_str)


@router.get("/", response_model=list[McpConnectionOut])
async def list_connections_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[McpConnectionOut]:
    connections = await mcp_connection_service.list_connections(db, user.id)
    return [_to_out(conn) for conn in connections]


@router.post("/", response_model=McpConnectionOut, status_code=201)
async def create_connection_endpoint(
    payload: McpConnectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> McpConnectionOut:
    conn = await mcp_connection_service.create_connection(db, user.id, payload)
    await db.commit()
    await db.refresh(conn)
    return _to_out(conn)


@router.get("/{connection_id}", response_model=McpConnectionOut)
async def get_connection_endpoint(
    connection_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> McpConnectionOut:
    conn = await mcp_connection_service.get_or_404(db, connection_id, user.id)
    return _to_out(conn)


@router.patch("/{connection_id}", response_model=McpConnectionOut)
async def update_connection_endpoint(
    connection_id: uuid.UUID,
    payload: McpConnectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> McpConnectionOut:
    conn = await mcp_connection_service.update_connection(db, connection_id, user.id, payload)
    await db.commit()
    await db.refresh(conn)
    return _to_out(conn)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection_endpoint(
    connection_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await mcp_connection_service.soft_delete_connection(db, connection_id, user.id)
    await db.commit()


@router.post("/{connection_id}/test", response_model=McpConnectionTestResult)
async def test_connection_endpoint(
    connection_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> McpConnectionTestResult:
    conn = await mcp_connection_service.get_or_404(db, connection_id, user.id)
    if conn.transport == McpConnectionTransport.sse.value:
        raise HTTPException(status_code=422, detail="SSE test-connection not yet supported")
    return await _run_stdio_test(conn, db)
