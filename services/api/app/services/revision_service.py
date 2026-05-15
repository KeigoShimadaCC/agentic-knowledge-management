from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.object import KosObject
from app.models.page import Page
from app.models.revision import ObjectRevision


async def snapshot_object_state(db: AsyncSession, object_id: uuid.UUID) -> dict[str, Any]:
    """Return a JSONB-safe snapshot of the current object (+ page if kind==page).

    Shape matches the contract in PHASE-7B-MCP-WRITE.md §8.
    """
    obj_result = await db.execute(select(KosObject).where(KosObject.id == object_id))
    obj = obj_result.scalar_one_or_none()
    if not obj:
        return {}

    snapshot: dict[str, Any] = {
        "object": {
            "title": obj.title,
            "description": obj.description,
            "tags": list(obj.tags or []),
            "metadata_": dict(obj.metadata_ or {}),
            "is_pinned": obj.is_pinned,
            "is_archived": obj.is_archived,
            "ai_generated": obj.ai_generated,
        }
    }

    if obj.kind == "page":
        page_result = await db.execute(select(Page).where(Page.id == object_id))
        page = page_result.scalar_one_or_none()
        if page:
            snapshot["page"] = {
                "content_text": page.content_text,
                "content_json": dict(page.content_json or {}),
                "word_count": page.word_count,
                "version": page.version,
            }

    return snapshot


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
