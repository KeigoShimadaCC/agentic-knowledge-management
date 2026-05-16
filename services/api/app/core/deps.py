from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.deleted_at.is_(None)).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=503, detail="No user found — run setup first")
    return user
