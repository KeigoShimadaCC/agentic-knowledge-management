import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.object import KosObject
from app.models.page import Page
from app.schemas.page import PageCreate, PageUpdate


def _count_words(text: str) -> int:
    return len(text.split()) if text.strip() else 0


async def create_page(
    db: AsyncSession, user_id: uuid.UUID, data: PageCreate
) -> tuple[KosObject, Page]:
    obj = KosObject(user_id=user_id, kind="page", title=data.title)
    db.add(obj)
    await db.flush()

    page = Page(
        id=obj.id,
        content_json=data.content_json,
        content_text="",
        word_count=0,
    )
    db.add(page)
    await db.flush()
    return obj, page


async def get_page_or_404(db: AsyncSession, page_id: uuid.UUID, user_id: uuid.UUID) -> Page:
    result = await db.execute(
        select(Page)
        .join(KosObject, KosObject.id == Page.id)
        .where(Page.id == page_id, KosObject.user_id == user_id, KosObject.deleted_at.is_(None))
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


async def update_page(
    db: AsyncSession, page_id: uuid.UUID, user_id: uuid.UUID, data: PageUpdate
) -> Page:
    page = await get_page_or_404(db, page_id, user_id)

    if data.expected_version is not None and page.version != data.expected_version:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Version conflict: expected {data.expected_version}, current is {page.version}."
            ),
        )

    if data.title is not None:
        obj_result = await db.execute(select(KosObject).where(KosObject.id == page_id))
        obj = obj_result.scalar_one()
        obj.title = data.title
        obj.updated_at = datetime.now(timezone.utc)

    if data.content_json is not None:
        page.content_json = data.content_json
    if data.content_text is not None:
        page.content_text = data.content_text
        page.word_count = _count_words(data.content_text)

    page.version += 1
    page.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return page
