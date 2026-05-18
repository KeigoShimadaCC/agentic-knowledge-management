import uuid
from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.object import KosObject
from app.schemas.common import PaginatedResponse
from app.schemas.object import ObjectCreate, ObjectOut, ObjectUpdate


async def create_object(db: AsyncSession, user_id: uuid.UUID, data: ObjectCreate) -> KosObject:
    obj = KosObject(
        user_id=user_id,
        kind=data.kind,
        title=data.title,
        description=data.description,
        tags=data.tags,
        metadata_=data.metadata_,
    )
    db.add(obj)
    await db.flush()
    return obj


async def get_object_or_404(
    db: AsyncSession, object_id: uuid.UUID, user_id: uuid.UUID
) -> KosObject:
    """Fetch a live (non-soft-deleted) object owned by user, or 404."""
    result = await db.execute(
        select(KosObject).where(
            KosObject.id == object_id,
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


async def get_object_or_404_including_deleted(
    db: AsyncSession, object_id: uuid.UUID, user_id: uuid.UUID
) -> KosObject:
    """Fetch any object (live or soft-deleted) owned by user, or 404.

    For restore-from-trash and revision-restore flows only.
    """
    result = await db.execute(
        select(KosObject).where(KosObject.id == object_id, KosObject.user_id == user_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


async def list_objects(
    db: AsyncSession,
    user_id: uuid.UUID,
    kind: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    include_deleted: bool = False,
    page: int = 1,
    limit: int = 20,
) -> PaginatedResponse[ObjectOut]:
    stmt = select(KosObject).where(KosObject.user_id == user_id)

    if not include_deleted:
        stmt = stmt.where(KosObject.deleted_at.is_(None))
    else:
        stmt = stmt.where(KosObject.deleted_at.is_not(None))

    if kind:
        stmt = stmt.where(KosObject.kind == kind)
    if tag:
        from sqlalchemy import any_

        stmt = stmt.where(tag == any_(KosObject.tags))
    if q:
        stmt = stmt.where(
            func.to_tsvector(
                "english",
                KosObject.title + " " + func.coalesce(KosObject.description, ""),
            ).op("@@")(func.plainto_tsquery("english", q))
        )

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar_one()

    stmt = stmt.order_by(KosObject.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ObjectOut.model_validate(obj) for obj in items],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, ceil(total / limit)),
    )


async def update_object(db: AsyncSession, obj: KosObject, data: ObjectUpdate) -> KosObject:
    if data.title is not None:
        obj.title = data.title
    if data.description is not None:
        obj.description = data.description
    if data.tags is not None:
        obj.tags = data.tags
    if data.metadata_ is not None:
        obj.metadata_ = data.metadata_
    if data.is_pinned is not None:
        obj.is_pinned = data.is_pinned
    if data.is_archived is not None:
        obj.is_archived = data.is_archived
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj


async def soft_delete_object(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj


async def restore_object(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = None
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj
