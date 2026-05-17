from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

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

    raise auth_service.unauthenticated()
