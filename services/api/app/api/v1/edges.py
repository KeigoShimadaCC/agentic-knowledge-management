import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.edge import Edge
from app.models.user import User
from app.schemas.edge import EdgeCreate, EdgeOut
from app.services import edge_service, object_service

router = APIRouter()


@router.post("", response_model=EdgeOut, status_code=201)
async def create_edge(
    body: EdgeCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOut:
    await object_service.get_object_or_404(db, body.source_id, user.id)
    await object_service.get_object_or_404(db, body.target_id, user.id)
    existing_edges = await edge_service.list_edges(
        db,
        source_id=body.source_id,
        target_id=body.target_id,
        kind=body.kind,
    )
    edge = await edge_service.create_edge(db, body.source_id, body.target_id, body.kind)
    await db.commit()
    await db.refresh(edge)
    if existing_edges:
        response.status_code = 200
    return EdgeOut.model_validate(edge)


@router.get("", response_model=list[EdgeOut])
async def list_edges(
    source_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    kind: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeOut]:
    edges = await edge_service.list_edges(db, source_id=source_id, target_id=target_id, kind=kind)
    return [EdgeOut.model_validate(edge) for edge in edges if edge.user_id == user.id]


@router.delete("/{edge_id}", response_model=EdgeOut)
async def delete_edge(
    edge_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOut:
    result = await db.execute(
        select(Edge).where(Edge.id == edge_id, Edge.user_id == user.id, Edge.deleted_at.is_(None))
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Edge not found")

    edge = await edge_service.delete_edge(db, edge_id)
    await db.commit()
    await db.refresh(edge)
    return EdgeOut.model_validate(edge)
