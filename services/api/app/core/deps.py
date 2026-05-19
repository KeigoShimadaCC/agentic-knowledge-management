from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services import auth_service


def _bearer_token(request: Request) -> str | None:
    value = request.headers.get("Authorization")
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise auth_service.unauthenticated()
    return token


async def _local_single_user_fallback(db: AsyncSession) -> User | None:
    """Return the deterministic first non-deleted user for the desktop single-user appliance.

    The desktop profile binds to 127.0.0.1 only, so only same-machine processes can
    reach the API. The mobile profile (KOS_PROFILE=mobile) is LAN-exposed and must
    keep requiring bearer/cookie auth — see app/middleware/lan_guard.py.

    ``ORDER BY created_at`` makes this stable across requests when the DB happens
    to accumulate multiple users (e.g. dev databases left over from earlier login
    flows). Without it, Postgres returns rows in arbitrary order and consecutive
    requests in the same test run can resolve to different users, causing
    ownership filters to 404 across requests.
    """
    if settings.kos_profile == "mobile":
        return None
    result = await db.execute(
        select(User).where(User.deleted_at.is_(None)).order_by(User.created_at).limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    bearer = _bearer_token(request)
    if bearer:
        user = await auth_service.resolve_user_from_session(db, bearer)
        if user:
            await db.commit()
            return user
        raise auth_service.unauthenticated()

    user = await auth_service.resolve_mcp_user(db, request.headers.get("X-KOS-Internal-Token"))
    if user:
        return user

    user = await auth_service.resolve_user_from_session(
        db, request.cookies.get(auth_service.SESSION_COOKIE)
    )
    if user:
        await db.commit()
        return user

    user = await _local_single_user_fallback(db)
    if user:
        return user

    raise auth_service.unauthenticated()
