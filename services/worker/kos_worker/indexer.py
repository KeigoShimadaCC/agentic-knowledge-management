"""Sync wrapper for embedding and Qdrant indexing - used by RQ tasks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def embed_and_upsert_chunks(db: Session, object_id: str, chunk_ids: list[str]) -> int:
    return asyncio.run(_async_embed_and_upsert(db, object_id, chunk_ids))


async def _async_embed_and_upsert(db: Session, object_id: str, chunk_ids: list[str]) -> int:
    from app.config import settings
    from app.models.chunk import Chunk
    from app.models.object import KosObject
    from app.models.source import Source
    from app.search import qdrant_client as qc
    from app.search.embedding import EmbeddingDisabledError, get_embedding_provider

    provider = get_embedding_provider()
    if not provider.is_enabled:
        logger.info("Embeddings disabled - skipping vector indexing for object %s", object_id)
        return 0

    chunks = [db.get(Chunk, uuid.UUID(cid)) for cid in chunk_ids]
    chunks = [c for c in chunks if c is not None]

    if not chunks:
        return 0

    obj = db.get(KosObject, uuid.UUID(object_id))
    if obj is None:
        return 0
    source = db.get(Source, obj.id) if obj.kind == "source" else None

    texts = [c.content for c in chunks]
    try:
        vectors = await provider.embed(texts)
    except EmbeddingDisabledError:
        return 0

    for chunk in chunks:
        chunk.embedding_status = "running"
    db.flush()

    points = []
    now_iso = datetime.now(UTC).isoformat()
    for chunk, vector in zip(chunks, vectors, strict=False):
        point_id = str(chunk.id)
        points.append(
            {
                "id": point_id,
                "vector": vector,
                "payload": {
                    "chunk_id": point_id,
                    "object_id": object_id,
                    "object_kind": obj.kind,
                    "title": obj.title or "",
                    "chunk_idx": chunk.chunk_idx,
                    "tags": obj.tags if obj.tags else [],
                    "source_type": source.source_type if source is not None else None,
                    "content_hash": chunk.content_hash,
                    "source_locator": chunk.source_locator,
                    "created_at": obj.created_at.isoformat() if obj.created_at else now_iso,
                    "updated_at": obj.updated_at.isoformat() if obj.updated_at else now_iso,
                    "content": chunk.content[:500],
                },
            }
        )

    try:
        await qc.create_collection_if_not_exists()
        await qc.delete_by_object_id(object_id)
        await qc.upsert_points(points)
    except Exception:
        for chunk in chunks:
            chunk.embedding_status = "error"
        db.commit()
        raise

    now = datetime.now(UTC)
    for chunk, point in zip(chunks, points, strict=False):
        chunk.embedding_status = "embedded"
        chunk.qdrant_point_id = point["id"]
        chunk.embedding_model = settings.embedding_model
        chunk.embedded_at = now

    db.commit()
    return len(chunks)
