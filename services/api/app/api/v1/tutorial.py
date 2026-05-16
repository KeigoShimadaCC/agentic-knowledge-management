from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import tutorial_seed_service

router = APIRouter(prefix="/tutorial", tags=["tutorial"])


class TutorialSeedOut(BaseModel):
    status: str
    seeded: bool


class TutorialResetOut(BaseModel):
    status: str
    reset: int


@router.post("/seed", response_model=TutorialSeedOut)
async def seed_tutorial(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TutorialSeedOut:
    seeded = await tutorial_seed_service.seed_tutorial(db, user.id)
    await db.commit()
    return TutorialSeedOut(status="ok", seeded=seeded)


@router.delete("/reset", response_model=TutorialResetOut)
async def reset_tutorial(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TutorialResetOut:
    reset = await tutorial_seed_service.reset_tutorial(db, user.id)
    await db.commit()
    return TutorialResetOut(status="ok", reset=reset)
