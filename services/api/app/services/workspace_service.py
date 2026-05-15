from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


async def create_workspace(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: WorkspaceCreate,
) -> Workspace:
    workspace = Workspace(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        layout_json=payload.layout.model_dump(mode="json"),
        is_pinned=payload.is_pinned,
    )
    db.add(workspace)
    await db.flush()
    return workspace


async def get_workspace(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    include_deleted: bool = False,
) -> Workspace | None:
    conditions = [
        Workspace.id == workspace_id,
        Workspace.user_id == user_id,
    ]
    if not include_deleted:
        conditions.append(Workspace.deleted_at.is_(None))

    stmt = select(Workspace).where(*conditions)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_workspaces(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    include_deleted: bool = False,
    pinned_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Workspace], int]:
    conditions = [Workspace.user_id == user_id]
    if not include_deleted:
        conditions.append(Workspace.deleted_at.is_(None))
    if pinned_only:
        conditions.append(Workspace.is_pinned.is_(True))

    total_stmt = select(func.count()).select_from(Workspace).where(*conditions)
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = (
        select(Workspace)
        .where(*conditions)
        .order_by(
            Workspace.is_pinned.desc(),
            Workspace.last_used_at.desc().nulls_last(),
            Workspace.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), int(total)


async def update_workspace(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
) -> Workspace | None:
    workspace = await get_workspace(db, user_id=user_id, workspace_id=workspace_id)
    if not workspace:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        workspace.name = updates["name"]
    if "description" in updates:
        workspace.description = updates["description"]
    if "layout" in updates:
        workspace.layout_json = payload.layout.model_dump(mode="json") if payload.layout else {}
    if "is_pinned" in updates:
        workspace.is_pinned = bool(updates["is_pinned"])

    workspace.updated_at = datetime.now(UTC)
    await db.flush()
    return workspace


async def soft_delete_workspace(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace | None:
    workspace = await get_workspace(
        db, user_id=user_id, workspace_id=workspace_id, include_deleted=True
    )
    if not workspace:
        return None
    if workspace.deleted_at is None:
        now = datetime.now(UTC)
        workspace.deleted_at = now
        workspace.updated_at = now
        await db.flush()
    return workspace


async def restore_workspace(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace | None:
    workspace = await get_workspace(
        db, user_id=user_id, workspace_id=workspace_id, include_deleted=True
    )
    if not workspace or workspace.deleted_at is None:
        return None

    workspace.deleted_at = None
    workspace.updated_at = datetime.now(UTC)
    await db.flush()
    return workspace


async def touch_last_used(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> Workspace | None:
    workspace = await get_workspace(db, user_id=user_id, workspace_id=workspace_id)
    if not workspace:
        return None

    workspace.last_used_at = datetime.now(UTC)
    await db.flush()
    return workspace
