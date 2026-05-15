import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import agent_id_from_request, get_redis
from app.db.session import get_db
from app.models.object import KosObject
from app.models.page import Page
from app.models.revision import ObjectRevision
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.edge import EdgeDirection, EdgeWithObjectsOut, RelatedObjectOut
from app.schemas.object import ObjectCreate, ObjectOut, ObjectUpdate
from app.services import edge_service, object_service
from app.services.audited_write_service import audited_write

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


@router.post("/{object_id}/archive", response_model=ObjectOut)
async def archive_object_endpoint(
    object_id: uuid.UUID,
    request: Request,
    reason: str | None = Body(default=None, embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ObjectOut:
    """Archive an object (flip is_archived=True). Idempotent: second call is a no-op.

    Creates agent_runs + object_revisions rows when the state actually changes.
    Rate-limited by the calling agent's identity (X-KOS-Agent-Id header).
    """
    # Fast idempotency check before touching the rate limiter or audit log
    obj_check = await object_service.get_object_or_404(db, object_id, user.id)
    if obj_check.is_archived:
        return ObjectOut.model_validate(obj_check)

    agent_id = agent_id_from_request(request)

    async def _do_archive(db: AsyncSession) -> KosObject:
        obj = await object_service.get_object_or_404(db, object_id, user.id)
        obj.is_archived = True
        obj.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return obj

    obj = await audited_write(
        db,
        redis,
        user_id=user.id,
        agent_id=agent_id,
        tool_name="archive_object",
        args={"object_id": str(object_id), "reason": reason},
        fn=_do_archive,
        mutating_object_id=object_id,
    )
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)


@router.post("/{object_id}/revisions/{rev_id}/restore", response_model=ObjectOut)
async def restore_revision_endpoint(
    object_id: uuid.UUID,
    rev_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ObjectOut:
    """Restore an object to the state captured in a prior revision's before_snapshot.

    Creates a new agent_runs row and a new object_revisions row recording the change.
    """
    # Validate revision ownership before rate-limit check
    rev_result = await db.execute(
        select(ObjectRevision).where(
            ObjectRevision.id == rev_id,
            ObjectRevision.object_id == object_id,
        )
    )
    revision = rev_result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    # Confirm user owns the object
    await object_service.get_object_or_404(db, object_id, user.id)

    agent_id = agent_id_from_request(request)

    async def _do_restore(db: AsyncSession) -> KosObject:
        obj_result = await db.execute(
            select(KosObject).where(KosObject.id == object_id, KosObject.user_id == user.id)
        )
        obj = obj_result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")

        snap = revision.before_snapshot
        obj_snap = snap.get("object", {})
        for field in ("title", "description", "tags", "is_pinned", "is_archived", "ai_generated"):
            if field in obj_snap:
                setattr(obj, field, obj_snap[field])
        if "metadata_" in obj_snap:
            obj.metadata_ = obj_snap["metadata_"]
        obj.updated_at = datetime.now(timezone.utc)
        await db.flush()

        page_snap = snap.get("page")
        if page_snap:
            page_result = await db.execute(select(Page).where(Page.id == object_id))
            page = page_result.scalar_one_or_none()
            if page:
                for field in ("content_text", "content_json", "word_count"):
                    if field in page_snap:
                        setattr(page, field, page_snap[field])
                page.version += 1
                page.updated_at = datetime.now(timezone.utc)
                await db.flush()

        return obj

    obj = await audited_write(
        db,
        redis,
        user_id=user.id,
        agent_id=agent_id,
        tool_name="restore_revision",
        args={"object_id": str(object_id), "rev_id": str(rev_id)},
        fn=_do_restore,
        mutating_object_id=object_id,
    )
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)
