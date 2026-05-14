import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.edge import EdgeCreate, EdgeOut
from app.services import edge_service

router = APIRouter()


@router.post("", response_model=EdgeOut, status_code=201)
async def create_edge(
    body: EdgeCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOut:
    existing_edges = await edge_service.list_edges(
        db,
        user_id=user.id,
        source_id=body.source_id,
        target_id=body.target_id,
        kind=body.kind,
        include_deleted=True,
    )
    edge = await edge_service.create_edge(
        db,
        body.source_id,
        body.target_id,
        body.kind,
        user_id=user.id,
        weight=body.weight,
        metadata_=body.metadata_,
    )
    await db.commit()
    await db.refresh(edge)
    if existing_edges and existing_edges[0].deleted_at is None:
        response.status_code = 200
    return EdgeOut.model_validate(edge)


@router.get("", response_model=list[EdgeOut])
async def list_edges(
    source_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    kind: str | None = None,
    include_deleted: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeOut]:
    edges = await edge_service.list_edges(
        db,
        user_id=user.id,
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        include_deleted=include_deleted,
    )
    return [EdgeOut.model_validate(edge) for edge in edges]


@router.delete("/{edge_id}", response_model=EdgeOut)
async def delete_edge(
    edge_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOut:
    edge = await edge_service.delete_edge(db, edge_id, user_id=user.id)
    await db.commit()
    await db.refresh(edge)
    return EdgeOut.model_validate(edge)
