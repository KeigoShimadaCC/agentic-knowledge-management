import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_token
from app.db.session import get_db
from app.models.session import Session
from app.models.user import User


async def _get_first_active_user(db: AsyncSession) -> User | None:
    result = await db.execute(
        select(User).where(User.deleted_at.is_(None)).limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    # MCP internal token path (only when token is configured and non-empty)
    internal_token = request.headers.get("X-KOS-Internal-Token", "")
    if (
        internal_token
        and settings.mcp_internal_token
        and secrets.compare_digest(
            internal_token.encode(), settings.mcp_internal_token.encode()
        )
    ):
        user = await _get_first_active_user(db)
        if user:
            return user

    # Cookie auth path
    token = request.cookies.get("kos_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hash_token(token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Session).where(
            Session.token_hash == token_hash,
            Session.expires_at > now,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user_result = await db.execute(
        select(User).where(User.id == session.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session.last_seen = now
    await db.commit()

    return user
