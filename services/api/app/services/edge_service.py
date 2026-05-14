import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge import Edge
from app.models.object import KosObject


async def create_edge(
    db: AsyncSession,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    kind: str,
) -> Edge:
    source_result = await db.execute(
        select(KosObject).where(KosObject.id == source_id, KosObject.deleted_at.is_(None))
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source object not found")

    target_result = await db.execute(
        select(KosObject).where(
            KosObject.id == target_id,
            KosObject.user_id == source.user_id,
            KosObject.deleted_at.is_(None),
        )
    )
    if target_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Target object not found")

    stmt = (
        insert(Edge)
        .values(
            user_id=source.user_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind,
        )
        .on_conflict_do_nothing(
            index_elements=["source_id", "target_id", "kind"],
        )
        .returning(Edge)
    )
    result = await db.execute(stmt)
    edge = result.scalar_one_or_none()
    if edge is not None:
        return edge

    existing_result = await db.execute(
        select(Edge).where(
            Edge.source_id == source_id,
            Edge.target_id == target_id,
            Edge.kind == kind,
        )
    )
    existing = existing_result.scalar_one()
    if existing.deleted_at is not None:
        existing.deleted_at = None
        await db.flush()
    return existing


async def list_edges(
    db: AsyncSession,
    source_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    kind: str | None = None,
) -> list[Edge]:
    stmt = select(Edge).where(Edge.deleted_at.is_(None))
    if source_id is not None:
        stmt = stmt.where(Edge.source_id == source_id)
    if target_id is not None:
        stmt = stmt.where(Edge.target_id == target_id)
    if kind is not None:
        stmt = stmt.where(Edge.kind == kind)

    result = await db.execute(stmt.order_by(Edge.created_at.desc()))
    return list(result.scalars().all())


async def delete_edge(db: AsyncSession, edge_id: uuid.UUID) -> Edge:
    result = await db.execute(select(Edge).where(Edge.id == edge_id, Edge.deleted_at.is_(None)))
    edge = result.scalar_one_or_none()
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")

    if hasattr(edge, "deleted_at"):
        edge.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return edge

    await db.execute(delete(Edge).where(Edge.id == edge_id))
    await db.flush()
    return edge
