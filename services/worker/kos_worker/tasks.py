import os
from datetime import UTC, datetime
from typing import Any

import redis
from app.models.ingestion_job import IngestionJob
from app.models.object import KosObject
from app.models.source import Source
from rq import Queue
from sqlalchemy import select

from kos_worker.db import get_session
from kos_worker.extractors import run_extractor

SEARCH_QUEUE_NAME = "kos-ingest"


def _now() -> datetime:
    return datetime.now(UTC)


def _apply_source_result(source: Source, result: dict[str, Any]) -> None:
    source_fields = set(Source.__mapper__.attrs.keys())
    for key, value in result.items():
        if key in source_fields:
            setattr(source, key, value)


def ingest_source(job_id: str) -> None:
    db = get_session()
    try:
        job = db.get(IngestionJob, job_id)
        if job is None:
            raise ValueError(f"Ingestion job not found: {job_id}")

        job.status = "running"
        job.started_at = _now()
        job.attempts = (job.attempts or 0) + 1

        source = db.get(Source, job.object_id)
        if source is None:
            raise ValueError(f"Source not found for ingestion job: {job_id}")

        source.ingestion_status = "running"
        db.commit()

        result = run_extractor(source, db)
        _apply_source_result(source, result)

        job.status = "success"
        job.result = result
        job.finished_at = _now()
        db.commit()

        enqueue_reindex_object(str(source.id))
    except Exception as exc:
        db.rollback()
        message = str(exc)

        if "job" in locals() and job is not None:
            job.status = "failed"
            job.error = message
            job.finished_at = _now()

        if "source" in locals() and source is not None:
            source.ingestion_status = "error"
            source.error_message = message

        db.commit()
        raise
    finally:
        db.close()


def _sync_chunk_object(object_id: str) -> list[str]:
    import asyncio
    import uuid as _uuid

    from app.db.session import AsyncSessionLocal
    from app.services.chunk_service import chunk_object as _async_chunk

    async def _run():
        async with AsyncSessionLocal() as db:
            chunks = await _async_chunk(db, _uuid.UUID(object_id))
            return [str(c.id) for c in chunks]

    return asyncio.run(_run())


def reindex_object(object_id: str) -> dict:
    """Chunk + embed + upsert one object. Safe to call multiple times (idempotent)."""
    import uuid as _uuid

    from kos_worker.indexer import embed_and_upsert_chunks

    db = get_session()
    try:
        obj = db.get(KosObject, _uuid.UUID(object_id))
        if obj is None or obj.deleted_at is not None:
            return {"skipped": True, "reason": "not_found_or_deleted"}

        chunk_ids = _sync_chunk_object(object_id)
        embedded_count = embed_and_upsert_chunks(db, object_id, chunk_ids)
        return {"object_id": object_id, "chunks": len(chunk_ids), "embedded": embedded_count}
    finally:
        db.close()


def reindex_all_objects() -> dict:
    """Enqueue reindex_object for every non-deleted page, source, and chat."""
    db = get_session()
    try:
        objects = (
            db.execute(
                select(KosObject).where(
                    KosObject.deleted_at.is_(None),
                    KosObject.kind.in_(["page", "source", "chat"]),
                )
            )
            .scalars()
            .all()
        )

        for obj in objects:
            enqueue_reindex_object(str(obj.id))

        return {"enqueued": len(objects)}
    finally:
        db.close()


def enqueue_reindex_object(object_id: str) -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    q = Queue(SEARCH_QUEUE_NAME, connection=redis.from_url(redis_url))
    q.enqueue(
        reindex_object,
        object_id,
        job_id=f"reindex:{object_id}",
    )
