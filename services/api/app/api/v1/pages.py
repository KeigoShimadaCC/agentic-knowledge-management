import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.object import ObjectOut
from app.schemas.page import PageCreate, PageOut, PageUpdate
from app.services import page_service

router = APIRouter(prefix="/pages", tags=["pages"])


class PageCreateResponse:
    def __init__(self, object: ObjectOut, page: PageOut):
        self.object = object
        self.page = page


from pydantic import BaseModel


class PageCreateOut(BaseModel):
    object: ObjectOut
    page: PageOut


@router.post("", response_model=PageCreateOut, status_code=201)
async def create_page(
    body: PageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageCreateOut:
    obj, page = await page_service.create_page(db, user.id, body)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(page)
    return PageCreateOut(object=ObjectOut.model_validate(obj), page=PageOut.model_validate(page))


@router.get("/{page_id}", response_model=PageOut)
async def get_page(
    page_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageOut:
    page = await page_service.get_page_or_404(db, page_id, user.id)
    return PageOut.model_validate(page)


@router.put("/{page_id}", response_model=PageOut)
async def replace_page(
    page_id: uuid.UUID,
    body: PageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageOut:
    page = await page_service.update_page(db, page_id, user.id, body)
    await db.commit()
    await db.refresh(page)
    return PageOut.model_validate(page)


@router.patch("/{page_id}", response_model=PageOut)
async def patch_page(
    page_id: uuid.UUID,
    body: PageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageOut:
    page = await page_service.update_page(db, page_id, user.id, body)
    await db.commit()
    await db.refresh(page)
    return PageOut.model_validate(page)
