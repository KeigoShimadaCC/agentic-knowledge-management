from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import generate_session_token, hash_token
from app.models.session import Session
from app.models.user import User

SESSION_COOKIE = "kos_session"
SESSION_DAYS = 30


def unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"detail": "Not authenticated", "code": "unauthenticated"},
    )


def session_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    client_type: str = "web",
    device_name: str | None = None,
) -> tuple[Session, str]:
    token = generate_session_token()
    session = Session(
        user_id=user.id,
        token_hash=hash_token(token),
        client_type=client_type,
        device_name=device_name,
        expires_at=session_expires_at(),
    )
    db.add(session)
    await db.flush()
    return session, token


async def resolve_session(db: AsyncSession, raw_token: str | None) -> Session | None:
    if not raw_token:
        return None

    result = await db.execute(
        select(Session, User)
        .join(User, User.id == Session.user_id)
        .where(
            Session.token_hash == hash_token(raw_token),
            Session.expires_at > datetime.now(timezone.utc),
            User.deleted_at.is_(None),
        )
    )
    row = result.one_or_none()
    if not row:
        return None

    session, _user = row
    session.last_seen = datetime.now(timezone.utc)
    await db.flush()
    return session


async def resolve_user_from_session(db: AsyncSession, raw_token: str | None) -> User | None:
    session = await resolve_session(db, raw_token)
    if session is None:
        return None

    result = await db.execute(
        select(User).where(User.id == session.user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def revoke_raw_token(db: AsyncSession, raw_token: str | None) -> bool:
    session = await resolve_session(db, raw_token)
    if session is None:
        return False
    await db.delete(session)
    await db.flush()
    return True


async def resolve_mcp_user(db: AsyncSession, token: str | None) -> User | None:
    configured = settings.mcp_internal_token
    if not configured or not token:
        return None
    if not secrets.compare_digest(token, configured):
        return None

    scoped = settings.mcp_internal_user_id
    if scoped:
        try:
            uid = uuid.UUID(scoped)
        except (ValueError, TypeError):
            return None
        result = await db.execute(
            select(User).where(User.id == uid, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    result = await db.execute(select(User).where(User.deleted_at.is_(None)).limit(1))
    return result.scalar_one_or_none()
