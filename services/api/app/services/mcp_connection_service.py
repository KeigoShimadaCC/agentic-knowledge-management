import fnmatch
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.mcp_client.crypto import encrypt_env_vars
from app.models.mcp_connection import McpConnection
from app.schemas.mcp_connection import McpConnectionCreate, McpConnectionUpdate


async def list_connections(db: AsyncSession, user_id: uuid.UUID) -> list[McpConnection]:
    """Return all non-deleted connections for the user, newest first."""
    result = await db.execute(
        select(McpConnection)
        .where(McpConnection.user_id == user_id, McpConnection.deleted_at.is_(None))
        .order_by(McpConnection.created_at.desc())
    )
    return list(result.scalars().all())


async def get_or_404(
    db: AsyncSession, connection_id: uuid.UUID, user_id: uuid.UUID
) -> McpConnection:
    """Get a connection owned by user or raise HTTPException(404)."""
    result = await db.execute(
        select(McpConnection).where(
            McpConnection.id == connection_id,
            McpConnection.user_id == user_id,
            McpConnection.deleted_at.is_(None),
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="MCP connection not found")
    return conn


def _validate_create(data: McpConnectionCreate) -> None:
    if data.transport == "stdio" and data.command is None:
        raise HTTPException(status_code=400, detail="command required for stdio transport")
    if data.transport == "sse" and data.url is None:
        raise HTTPException(status_code=400, detail="url required for sse transport")
    if data.env_vars and not settings.mcp_env_encryption_key:
        raise HTTPException(status_code=400, detail="MCP_ENV_ENCRYPTION_KEY not configured")


def _encrypt_env_vars_or_400(env_vars: dict[str, str]) -> dict[str, str]:
    if env_vars and not settings.mcp_env_encryption_key:
        raise HTTPException(status_code=400, detail="MCP_ENV_ENCRYPTION_KEY not configured")
    return encrypt_env_vars(env_vars)


async def create_connection(
    db: AsyncSession, user_id: uuid.UUID, data: McpConnectionCreate
) -> McpConnection:
    """
    Validate transport constraints, encrypt env_vars, persist.
    - stdio: command must be non-None.
    - sse: url must be non-None.
    - env_vars require settings.mcp_env_encryption_key.
    - Encrypt env_vars before storing.
    - flush() but DO NOT commit (caller commits).
    """
    _validate_create(data)
    conn = McpConnection(
        user_id=user_id,
        name=data.name,
        transport=data.transport.value,
        command=data.command,
        args=data.args,
        url=data.url,
        env_vars=_encrypt_env_vars_or_400(data.env_vars),
        enabled=data.enabled,
    )
    db.add(conn)
    await db.flush()
    return conn


async def update_connection(
    db: AsyncSession, connection_id: uuid.UUID, user_id: uuid.UUID, data: McpConnectionUpdate
) -> McpConnection:
    """
    Update fields. Re-encrypt env_vars if provided.
    - flush() but DO NOT commit.
    """
    conn = await get_or_404(db, connection_id, user_id)
    updates = data.model_dump(exclude_unset=True)

    if "name" in updates:
        conn.name = updates["name"]
    if "command" in updates:
        conn.command = updates["command"]
    if "args" in updates:
        conn.args = updates["args"] or []
    if "url" in updates:
        conn.url = updates["url"]
    if "env_vars" in updates:
        conn.env_vars = _encrypt_env_vars_or_400(updates["env_vars"] or {})
    if "enabled" in updates:
        conn.enabled = bool(updates["enabled"])

    conn.updated_at = datetime.now(UTC)
    await db.flush()
    return conn


async def soft_delete_connection(
    db: AsyncSession, connection_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Set deleted_at = now(). flush() but DO NOT commit."""
    conn = await get_or_404(db, connection_id, user_id)
    now = datetime.now(UTC)
    conn.deleted_at = now
    conn.updated_at = now
    await db.flush()


async def cache_capabilities(db: AsyncSession, conn: McpConnection, tools: list[dict]) -> None:
    """
    Write capabilities (list of tool dicts) and last_tested_at to the connection row.
    Clear last_error. flush() but DO NOT commit.
    """
    conn.capabilities = tools
    conn.last_tested_at = datetime.now(UTC)
    conn.last_error = None
    conn.updated_at = datetime.now(UTC)
    await db.flush()


async def record_test_error(db: AsyncSession, conn: McpConnection, error: str) -> None:
    """Write last_error, clear last_tested_at. flush() but DO NOT commit."""
    conn.last_error = error
    conn.last_tested_at = None
    conn.updated_at = datetime.now(UTC)
    await db.flush()


async def find_connection_for_patterns(
    db: AsyncSession,
    user_id: uuid.UUID,
    patterns: list[str],
    preferred_name: str = "",
) -> McpConnection | None:
    """Return first enabled connection with a cached tool matching any pattern."""
    connections = await list_connections(db, user_id)
    if preferred_name:
        connections = sorted(connections, key=lambda c: c.name != preferred_name)
    for conn in connections:
        if not conn.enabled or not conn.capabilities:
            continue
        for tool in conn.capabilities:
            tool_name = tool["name"] if isinstance(tool, dict) else tool.name
            if any(fnmatch.fnmatch(tool_name, p) for p in patterns):
                return conn
    return None
