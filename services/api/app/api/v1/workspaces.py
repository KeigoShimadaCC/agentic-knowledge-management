from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.common import PaginatedResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceLayout, WorkspaceOut, WorkspaceUpdate
from app.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _build_workspace_out(workspace: Workspace) -> WorkspaceOut:
    return WorkspaceOut(
        id=workspace.id,
        user_id=workspace.user_id,
        name=workspace.name,
        description=workspace.description,
        layout=WorkspaceLayout.model_validate(workspace.layout_json),
        is_pinned=workspace.is_pinned,
        last_used_at=workspace.last_used_at,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        deleted_at=workspace.deleted_at,
    )


@router.post("", response_model=WorkspaceOut, status_code=201)
async def create_workspace_endpoint(
    payload: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    workspace = await workspace_service.create_workspace(db, user_id=user.id, payload=payload)
    await db.commit()
    await db.refresh(workspace)
    return _build_workspace_out(workspace)


@router.get("", response_model=PaginatedResponse[WorkspaceOut])
async def list_workspaces_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pinned_only: bool = Query(False),
    include_deleted: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[WorkspaceOut]:
    rows, total = await workspace_service.list_workspaces(
        db,
        user_id=user.id,
        include_deleted=include_deleted,
        pinned_only=pinned_only,
        limit=limit,
        offset=offset,
    )
    page = offset // limit + 1 if limit else 1
    pages = (total + limit - 1) // limit if total and limit else 0
    return PaginatedResponse(
        items=[_build_workspace_out(row) for row in rows],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace_endpoint(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    workspace = await workspace_service.touch_last_used(
        db, user_id=user.id, workspace_id=workspace_id
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.commit()
    await db.refresh(workspace)
    return _build_workspace_out(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace_endpoint(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    workspace = await workspace_service.update_workspace(
        db, user_id=user.id, workspace_id=workspace_id, payload=payload
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.commit()
    await db.refresh(workspace)
    return _build_workspace_out(workspace)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace_endpoint(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    workspace = await workspace_service.soft_delete_workspace(
        db, user_id=user.id, workspace_id=workspace_id
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.commit()


@router.post("/{workspace_id}/restore", response_model=WorkspaceOut)
async def restore_workspace_endpoint(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    workspace = await workspace_service.restore_workspace(
        db, user_id=user.id, workspace_id=workspace_id
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.commit()
    await db.refresh(workspace)
    return _build_workspace_out(workspace)
