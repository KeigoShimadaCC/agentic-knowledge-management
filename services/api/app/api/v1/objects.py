import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.object import ObjectCreate, ObjectOut, ObjectUpdate
from app.services import object_service

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("", response_model=PaginatedResponse[ObjectOut])
async def list_objects(
    kind: str | None = Query(None),
    tag: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ObjectOut]:
    return await object_service.list_objects(db, user.id, kind=kind, tag=tag, q=q, page=page, limit=limit)


@router.get("/trash", response_model=PaginatedResponse[ObjectOut])
async def list_trash(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ObjectOut]:
    return await object_service.list_objects(db, user.id, include_deleted=True, page=page, limit=limit)


@router.post("", response_model=ObjectOut, status_code=201)
async def create_object(
    body: ObjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    obj = await object_service.create_object(db, user.id, body)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)


@router.get("/{object_id}", response_model=ObjectOut)
async def get_object(
    object_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    obj = await object_service.get_object_or_404(db, object_id, user.id)
    return ObjectOut.model_validate(obj)


@router.patch("/{object_id}", response_model=ObjectOut)
async def update_object(
    object_id: uuid.UUID,
    body: ObjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    obj = await object_service.get_object_or_404(db, object_id, user.id)
    obj = await object_service.update_object(db, obj, body)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)


@router.delete("/{object_id}", response_model=ObjectOut)
async def delete_object(
    object_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    obj = await object_service.get_object_or_404(db, object_id, user.id)
    obj = await object_service.soft_delete_object(db, obj)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)


@router.post("/{object_id}/restore", response_model=ObjectOut)
async def restore_object(
    object_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    obj = await object_service.get_object_or_404(db, object_id, user.id)
    obj = await object_service.restore_object(db, obj)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)
