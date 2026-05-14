import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.edge_kinds import validate_edge_kind
from app.models.edge import Edge
from app.models.object import KosObject
from app.schemas.edge import EdgeWithObjectsOut, ObjectSummary, RelatedObjectOut

Direction = Literal["incoming", "outgoing", "both"]


@dataclass(frozen=True)
class EdgeRecord:
    edge: Edge
    source: KosObject
    target: KosObject
    direction: Literal["incoming", "outgoing"] | None = None


async def create_edge(
    db: AsyncSession,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    kind: str,
    *,
    user_id: uuid.UUID | None = None,
    weight: float = 1.0,
    metadata_: dict | None = None,
) -> Edge:
    validate_edge_kind(kind)

    source = await _get_owned_live_object(db, source_id, user_id, "Source object not found")
    await _get_owned_live_object(db, target_id, source.user_id, "Target object not found")

    stmt = (
        insert(Edge)
        .values(
            user_id=source.user_id,
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            weight=weight,
            metadata_=metadata_ or {},
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
        existing.weight = weight
        existing.metadata_ = metadata_ or existing.metadata_ or {}
        await db.flush()
    return existing


async def list_edges(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    kind: str | None = None,
    include_deleted: bool = False,
) -> list[Edge]:
    if kind is not None:
        validate_edge_kind(kind)

    stmt = select(Edge)
    if user_id is not None:
        stmt = stmt.where(Edge.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Edge.deleted_at.is_(None))
    if source_id is not None:
        stmt = stmt.where(Edge.source_id == source_id)
    if target_id is not None:
        stmt = stmt.where(Edge.target_id == target_id)
    if kind is not None:
        stmt = stmt.where(Edge.kind == kind)

    result = await db.execute(stmt.order_by(Edge.created_at.desc()))
    return list(result.scalars().all())


async def list_object_edges(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
    direction: Direction = "both",
    kind: str | None = None,
    include_deleted: bool = False,
) -> list[EdgeRecord]:
    if kind is not None:
        validate_edge_kind(kind)
    await _get_owned_object(db, object_id, user_id, include_deleted=False)

    stmt = select(Edge)
    stmt = stmt.where(Edge.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Edge.deleted_at.is_(None))
    if kind is not None:
        stmt = stmt.where(Edge.kind == kind)

    if direction == "incoming":
        stmt = stmt.where(Edge.target_id == object_id)
    elif direction == "outgoing":
        stmt = stmt.where(Edge.source_id == object_id)
    else:
        stmt = stmt.where(or_(Edge.source_id == object_id, Edge.target_id == object_id))

    result = await db.execute(stmt.order_by(Edge.created_at.desc()))
    edges = list(result.scalars().all())
    return await _hydrate_edge_records(
        db,
        edges,
        relative_to=object_id,
        include_deleted=include_deleted,
    )


async def get_related_objects(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    object_id: uuid.UUID,
    depth: int = 1,
    edge_types: list[str] | None = None,
    direction: Direction = "both",
    limit: int = 20,
) -> list[RelatedObjectOut]:
    if depth < 1 or depth > 2:
        raise HTTPException(status_code=422, detail="depth must be 1 or 2")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if edge_types:
        for edge_type in edge_types:
            validate_edge_kind(edge_type)

    await _get_owned_object(db, object_id, user_id, include_deleted=False)

    first_hop = await list_object_edges(
        db,
        user_id=user_id,
        object_id=object_id,
        direction=direction,
        include_deleted=False,
    )
    if edge_types:
        first_hop = [record for record in first_hop if record.edge.kind in edge_types]

    by_object: dict[uuid.UUID, tuple[int, float, list[EdgeRecord]]] = {}
    visited = {object_id}

    def add_related(related_id: uuid.UUID, distance: int, records: list[EdgeRecord]) -> None:
        if related_id in visited:
            return
        score = _score_related(distance, records)
        current = by_object.get(related_id)
        if current is None or score > current[1]:
            by_object[related_id] = (distance, score, records)

    first_neighbors: list[uuid.UUID] = []
    for record in first_hop:
        related_id = _other_object_id(record.edge, object_id)
        first_neighbors.append(related_id)
        add_related(related_id, 1, [record])

    if depth == 2:
        for neighbor_id in first_neighbors:
            visited.add(neighbor_id)
            second_hop = await list_object_edges(
                db,
                user_id=user_id,
                object_id=neighbor_id,
                direction=direction,
                include_deleted=False,
            )
            if edge_types:
                second_hop = [record for record in second_hop if record.edge.kind in edge_types]
            first_record = by_object.get(neighbor_id)
            if first_record is None:
                continue
            first_path = first_record[2]
            for second_record in second_hop:
                second_related_id = _other_object_id(second_record.edge, neighbor_id)
                add_related(second_related_id, 2, [*first_path, second_record])

    sorted_items = sorted(by_object.items(), key=lambda item: (item[1][0], -item[1][1]))
    return [
        RelatedObjectOut(
            object=ObjectSummary.model_validate(await _get_owned_object(db, related_id, user_id)),
            distance=distance,
            score=score,
            via_edges=[_edge_record_to_out(record) for record in records],
        )
        for related_id, (distance, score, records) in sorted_items[:limit]
    ]


async def delete_edge(
    db: AsyncSession,
    edge_id: uuid.UUID,
    *,
    user_id: uuid.UUID | None = None,
) -> Edge:
    stmt = select(Edge).where(Edge.id == edge_id, Edge.deleted_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(Edge.user_id == user_id)
    result = await db.execute(stmt)
    edge = result.scalar_one_or_none()
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")

    edge.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return edge


async def _get_owned_live_object(
    db: AsyncSession,
    object_id: uuid.UUID,
    user_id: uuid.UUID | None,
    not_found_detail: str,
) -> KosObject:
    obj = await _get_owned_object(db, object_id, user_id, include_deleted=False)
    if obj is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return obj


async def _get_owned_object(
    db: AsyncSession,
    object_id: uuid.UUID,
    user_id: uuid.UUID | None,
    *,
    include_deleted: bool = False,
) -> KosObject:
    stmt = select(KosObject).where(KosObject.id == object_id)
    if user_id is not None:
        stmt = stmt.where(KosObject.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(KosObject.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


async def _hydrate_edge_records(
    db: AsyncSession,
    edges: list[Edge],
    *,
    relative_to: uuid.UUID | None = None,
    include_deleted: bool = False,
) -> list[EdgeRecord]:
    if not edges:
        return []

    object_ids = {edge.source_id for edge in edges} | {edge.target_id for edge in edges}
    stmt = select(KosObject).where(KosObject.id.in_(object_ids))
    if not include_deleted:
        stmt = stmt.where(KosObject.deleted_at.is_(None))
    result = await db.execute(stmt)
    objects = {obj.id: obj for obj in result.scalars().all()}

    records: list[EdgeRecord] = []
    for edge in edges:
        source = objects.get(edge.source_id)
        target = objects.get(edge.target_id)
        if source is None or target is None:
            continue
        edge_direction: Literal["incoming", "outgoing"] | None = None
        if relative_to is not None:
            edge_direction = "outgoing" if edge.source_id == relative_to else "incoming"
        records.append(
            EdgeRecord(edge=edge, source=source, target=target, direction=edge_direction)
        )
    return records


def _edge_record_to_out(record: EdgeRecord) -> EdgeWithObjectsOut:
    return EdgeWithObjectsOut(
        id=record.edge.id,
        user_id=record.edge.user_id,
        source_id=record.edge.source_id,
        target_id=record.edge.target_id,
        kind=record.edge.kind,
        weight=record.edge.weight,
        metadata=record.edge.metadata_,
        created_at=record.edge.created_at,
        deleted_at=record.edge.deleted_at,
        source=ObjectSummary.model_validate(record.source),
        target=ObjectSummary.model_validate(record.target),
        direction=record.direction,
    )


def edge_record_to_out(record: EdgeRecord) -> EdgeWithObjectsOut:
    return _edge_record_to_out(record)


def _other_object_id(edge: Edge, object_id: uuid.UUID) -> uuid.UUID:
    return edge.target_id if edge.source_id == object_id else edge.source_id


def _score_related(distance: int, records: list[EdgeRecord]) -> float:
    weight = sum(record.edge.weight for record in records)
    direct_bonus = 10.0 if distance == 1 else 0.0
    return direct_bonus + weight / distance
