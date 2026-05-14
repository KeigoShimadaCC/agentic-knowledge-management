import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ingestion_job import IngestionJob
from app.models.object import KosObject
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceUpdate

logger = logging.getLogger(__name__)
INGEST_QUEUE_NAME = "kos-ingest"


async def ensure_source_dir(source_id: str) -> Path:
    path = settings.library_root / "sources" / source_id
    path.mkdir(parents=True, exist_ok=True)
    return path


async def create_source(
    db: AsyncSession, user_id: uuid.UUID, data: SourceCreate
) -> tuple[KosObject, Source]:
    obj = KosObject(
        user_id=user_id,
        kind="source",
        title=data.title,
        description=data.description,
        tags=data.tags,
    )
    db.add(obj)
    await db.flush()

    source = Source(
        id=obj.id,
        source_type=data.source_type,
        url=data.url,
        asset_id=data.asset_id,
        ingestion_status="pending",
    )
    db.add(source)
    await db.flush()

    job = IngestionJob(
        user_id=user_id,
        object_id=source.id,
        status="pending",
        job_type="source_ingestion",
        payload={"source_id": str(source.id)},
    )
    db.add(job)
    await db.flush()

    try:
        redis_conn = Redis.from_url(settings.redis_url)
        queue = Queue(INGEST_QUEUE_NAME, connection=redis_conn)
        await asyncio.to_thread(
            queue.enqueue,
            "kos_worker.tasks.ingest_source",
            str(job.id),
        )
    except Exception:
        logger.warning("Failed to enqueue source ingestion job", exc_info=True)

    return obj, source


async def get_source_or_404(
    db: AsyncSession, source_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[KosObject, Source]:
    result = await db.execute(
        select(KosObject, Source)
        .join(Source, Source.id == KosObject.id)
        .where(KosObject.id == source_id, KosObject.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    obj, source = row
    if obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Source not found")
    return obj, source


async def get_source_for_restore_or_404(
    db: AsyncSession, source_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[KosObject, Source]:
    result = await db.execute(
        select(KosObject, Source)
        .join(Source, Source.id == KosObject.id)
        .where(KosObject.id == source_id, KosObject.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    obj, source = row
    return obj, source


async def list_sources(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_type: str | None = None,
    ingestion_status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple[KosObject, Source]]:
    stmt = (
        select(KosObject, Source)
        .join(Source, Source.id == KosObject.id)
        .where(KosObject.user_id == user_id, KosObject.deleted_at.is_(None))
    )

    if source_type:
        stmt = stmt.where(Source.source_type == source_type)
    if ingestion_status:
        stmt = stmt.where(Source.ingestion_status == ingestion_status)
    if q:
        stmt = stmt.where(KosObject.title.ilike(f"%{q}%"))

    stmt = stmt.order_by(KosObject.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def update_source(db: AsyncSession, obj: KosObject, data: SourceUpdate) -> KosObject:
    if data.title is not None:
        obj.title = data.title
    if data.description is not None:
        obj.description = data.description
    if data.tags is not None:
        obj.tags = data.tags
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj


async def soft_delete_source(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj


async def restore_source(db: AsyncSession, obj: KosObject) -> KosObject:
    obj.deleted_at = None
    obj.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return obj
