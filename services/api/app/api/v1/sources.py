import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.object import KosObject
from app.models.source import Source
from app.models.user import User
from app.schemas.source import SourceCreate, SourceOut, SourceUpdate
from app.services import reindex_service, source_service

router = APIRouter()


def build_source_out(obj: KosObject, source: Source) -> SourceOut:
    return SourceOut(
        id=obj.id,
        user_id=obj.user_id,
        kind=obj.kind,
        title=obj.title,
        description=obj.description,
        tags=obj.tags,
        is_pinned=obj.is_pinned,
        is_archived=obj.is_archived,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        deleted_at=obj.deleted_at,
        source_type=source.source_type,
        url=source.url,
        asset_id=source.asset_id,
        ingestion_status=source.ingestion_status,
        extracted_text=source.extracted_text,
        page_count=source.page_count,
        thumbnail_path=source.thumbnail_path,
        preview_data=source.preview_data,
        error_message=source.error_message,
    )


@router.post("", response_model=SourceOut, status_code=201)
async def create_source(
    body: SourceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    obj, source, job = await source_service.create_source(db, user.id, body)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(source)
    try:
        await source_service.enqueue_source_ingestion(job.id)
    except Exception:
        pass
    return build_source_out(obj, source)


@router.get("", response_model=list[SourceOut])
async def list_sources(
    source_type: str | None = None,
    ingestion_status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SourceOut]:
    rows = await source_service.list_sources(
        db,
        user.id,
        source_type=source_type,
        ingestion_status=ingestion_status,
        q=q,
        skip=skip,
        limit=limit,
    )
    return [build_source_out(obj, source) for obj, source in rows]


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    obj, source = await source_service.get_source_or_404(db, source_id, user.id)
    return build_source_out(obj, source)


@router.patch("/{source_id}", response_model=SourceOut)
async def patch_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    obj, source = await source_service.get_source_or_404(db, source_id, user.id)
    obj = await source_service.update_source(db, obj, body)
    await db.commit()
    reindex_service.enqueue_reindex_object(obj.id)
    await db.refresh(obj)
    await db.refresh(source)
    return build_source_out(obj, source)


@router.delete("/{source_id}", response_model=SourceOut)
async def delete_source(
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    obj, source = await source_service.get_source_or_404(db, source_id, user.id)
    obj = await source_service.soft_delete_source(db, obj)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(source)
    return build_source_out(obj, source)


@router.post("/{source_id}/restore", response_model=SourceOut)
async def restore_source(
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    obj, source = await source_service.get_source_for_restore_or_404(db, source_id, user.id)
    obj = await source_service.restore_source(db, obj)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(source)
    return build_source_out(obj, source)


@router.get("/{source_id}/text")
async def get_source_text(
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    _, source = await source_service.get_source_or_404(db, source_id, user.id)
    if not source.extracted_text:
        raise HTTPException(status_code=404, detail="Source text not found")
    return StreamingResponse(iter([source.extracted_text]), media_type="text/plain")


@router.get("/{source_id}/thumbnail")
async def get_source_thumbnail(
    source_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    _, source = await source_service.get_source_or_404(db, source_id, user.id)
    if not source.thumbnail_path:
        raise HTTPException(status_code=404, detail="Source thumbnail not found")
    thumbnail_path = settings.library_root / source.thumbnail_path
    if not thumbnail_path.exists():
        raise HTTPException(status_code=404, detail="Source thumbnail not found")
    return FileResponse(path=str(thumbnail_path))
