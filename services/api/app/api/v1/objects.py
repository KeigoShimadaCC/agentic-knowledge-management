import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.edge import EdgeDirection, EdgeWithObjectsOut, RelatedObjectOut
from app.schemas.object import ObjectCreate, ObjectOut, ObjectUpdate
from app.services import edge_service, object_service

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
    return await object_service.list_objects(
        db,
        user.id,
        kind=kind,
        tag=tag,
        q=q,
        page=page,
        limit=limit,
    )


@router.get("/trash", response_model=PaginatedResponse[ObjectOut])
async def list_trash(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ObjectOut]:
    return await object_service.list_objects(
        db,
        user.id,
        include_deleted=True,
        page=page,
        limit=limit,
    )


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


@router.get("/{object_id}/edges", response_model=list[EdgeWithObjectsOut])
async def list_object_edges(
    object_id: uuid.UUID,
    direction: EdgeDirection = Query("both"),
    kind: str | None = Query(None),
    include_deleted: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeWithObjectsOut]:
    records = await edge_service.list_object_edges(
        db,
        user_id=user.id,
        object_id=object_id,
        direction=direction,
        kind=kind,
        include_deleted=include_deleted,
    )
    return [edge_service.edge_record_to_out(record) for record in records]


@router.get("/{object_id}/backlinks", response_model=list[EdgeWithObjectsOut])
async def list_object_backlinks(
    object_id: uuid.UUID,
    kind: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeWithObjectsOut]:
    records = await edge_service.list_object_edges(
        db,
        user_id=user.id,
        object_id=object_id,
        direction="incoming",
        kind=kind,
        include_deleted=False,
    )
    return [edge_service.edge_record_to_out(record) for record in records]


@router.get("/{object_id}/related", response_model=list[RelatedObjectOut])
async def list_related_objects(
    object_id: uuid.UUID,
    depth: int = Query(1, ge=1, le=2),
    edge_types: list[str] | None = Query(None),
    direction: EdgeDirection = Query("both"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RelatedObjectOut]:
    return await edge_service.get_related_objects(
        db,
        user_id=user.id,
        object_id=object_id,
        depth=depth,
        edge_types=edge_types,
        direction=direction,
        limit=limit,
    )


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
