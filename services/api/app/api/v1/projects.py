from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.object import KosObject
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectStatus, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_project_out(obj: KosObject, proj: Project) -> ProjectOut:
    return ProjectOut(
        id=obj.id,
        user_id=obj.user_id,
        title=obj.title,
        description=obj.description,
        period_start=proj.period_start,
        period_end=proj.period_end,
        role=proj.role,
        organization=proj.organization,
        problem=proj.problem,
        actions=proj.actions,
        results=proj.results,
        metrics=dict(proj.metrics or {}),
        skills=list(proj.skills or []),
        status=proj.status,  # type: ignore[arg-type]
        tags=list(obj.tags or []),
        is_pinned=obj.is_pinned,
        is_archived=obj.is_archived,
        confidence=proj.confidence,  # type: ignore[arg-type]
        extracted_from=proj.extracted_from,
        extracted_by_agent_run_id=proj.extracted_by_agent_run_id,
        created_at=obj.created_at,
        updated_at=proj.updated_at,
        deleted_at=obj.deleted_at,
    )


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project_endpoint(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    obj, proj = await project_service.create_project(db, user_id=user.id, payload=payload)
    await db.commit()
    await db.refresh(obj)
    await db.refresh(proj)
    return _build_project_out(obj, proj)


@router.get("", response_model=PaginatedResponse[ProjectOut])
async def list_projects_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: ProjectStatus | None = Query(None),
    skill: str | None = Query(None, min_length=1, max_length=64),
    include_archived: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectOut]:
    rows, total = await project_service.list_projects(
        db,
        user_id=user.id,
        limit=limit,
        offset=offset,
        status=status,
        skill=skill,
        include_archived=include_archived,
    )
    items = [_build_project_out(o, p) for o, p in rows]
    page = offset // limit + 1 if limit else 1
    pages = (total + limit - 1) // limit if total and limit else 0
    return PaginatedResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project_endpoint(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    row = await project_service.get_project(db, project_id=project_id, user_id=user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    obj, proj = row
    return _build_project_out(obj, proj)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project_endpoint(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    row = await project_service.update_project(
        db, project_id=project_id, user_id=user.id, payload=payload
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    obj, proj = row
    await db.commit()
    await db.refresh(obj)
    await db.refresh(proj)
    return _build_project_out(obj, proj)


@router.delete("/{project_id}", status_code=204)
async def delete_project_endpoint(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await project_service.soft_delete_project(db, project_id=project_id, user_id=user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.commit()
