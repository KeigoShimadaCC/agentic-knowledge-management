from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.revision import ObjectRevision


async def create_revision(
    db: AsyncSession,
    *,
    object_id: uuid.UUID,
    user_id: uuid.UUID,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    changed_by: str,
    agent_run_id: uuid.UUID | None = None,
) -> ObjectRevision:
    result = await db.execute(
        select(func.max(ObjectRevision.rev_num)).where(ObjectRevision.object_id == object_id)
    )
    rev_num = (result.scalar_one_or_none() or 0) + 1
    revision = ObjectRevision(
        object_id=object_id,
        user_id=user_id,
        rev_num=rev_num,
        changed_by=changed_by,
        agent_run_id=agent_run_id,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    db.add(revision)
    await db.flush()
    return revision
