from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MobileLoginRequest,
    MobileLoginResponse,
    RegisterRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=auth_service.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=auth_service.SESSION_DAYS * 24 * 3600,
        path="/",
    )


@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    if not settings.allow_open_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Unable to complete registration")

    user = User(
        email=body.email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    _session, token = await auth_service.create_session(db, user)
    await db.commit()
    await db.refresh(user)

    _set_session_cookie(response, token)
    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _session, token = await auth_service.create_session(db, user)
    await db.commit()

    _set_session_cookie(response, token)
    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/mobile-login", response_model=MobileLoginResponse)
async def mobile_login(
    body: MobileLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> MobileLoginResponse:
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session, token = await auth_service.create_session(
        db,
        user,
        client_type="ios",
        device_name=body.device_name,
    )
    await db.commit()
    await db.refresh(user)

    return MobileLoginResponse(
        token=token,
        user=UserOut.model_validate(user),
        expires_at=session.expires_at,
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = request.cookies.get(auth_service.SESSION_COOKIE)
    if token and await auth_service.revoke_raw_token(db, token):
        await db.commit()

    response.delete_cookie(key=auth_service.SESSION_COOKIE, path="/", secure=settings.cookie_secure)
    return {"ok": True}


@router.post("/mobile-logout")
async def mobile_logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    value = request.headers.get("Authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise auth_service.unauthenticated()

    if not await auth_service.revoke_raw_token(db, token):
        raise auth_service.unauthenticated()
    await db.commit()
    return {"ok": True}


@router.get("/me", response_model=AuthResponse)
async def me(user: User = Depends(get_current_user)) -> AuthResponse:
    return AuthResponse(user=UserOut.model_validate(user))
