"""Interactive tutorial seed content.

Idempotent per user via objects.tags marker tutorial_v1.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import any_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.object import KosObject
from app.schemas.page import PageCreate, PageUpdate
from app.schemas.project import ProjectCreate
from app.schemas.source import SourceCreate
from app.services import (
    agent_run_service,
    edge_service,
    page_service,
    project_service,
    source_service,
)

TUTORIAL_TAG = "tutorial_v1"


def _doc(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(blocks)}


def _text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


def _paragraph(value: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": [_text(value)]}


def _heading(level: int, value: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(value)]}


async def has_tutorial_seed(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(KosObject.id)
        .where(
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
            TUTORIAL_TAG == any_(KosObject.tags),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def seed_tutorial(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Seed tutorial objects for the current user. Returns True when new rows were created."""
    if await has_tutorial_seed(db, user_id):
        return False

    run = await agent_run_service.create_agent_run(
        db,
        user_id=user_id,
        agent_type="tutorial_seed",
        input_payload={"tag": TUTORIAL_TAG},
        model=None,
    )

    try:
        pages = [
            (
                "Welcome to KnowledgeOS",
                _doc(
                    _heading(1, "Welcome to KnowledgeOS"),
                    _paragraph(
                        "This starter page gives you a safe place to try pages, "
                        "search, and graph links."
                    ),
                ),
                (
                    "Welcome to KnowledgeOS. This starter page gives you a safe place to try "
                    "pages, search, and graph links."
                ),
            ),
            (
                "Reading Notes: Getting Things Done",
                _doc(
                    _heading(1, "Reading Notes: Getting Things Done"),
                    _paragraph(
                        "Capture trusted notes, then connect them to projects, "
                        "sources, and future decisions."
                    ),
                ),
                (
                    "Reading Notes: Getting Things Done. Capture trusted notes, then connect "
                    "them to projects, sources, and future decisions."
                ),
            ),
            (
                "Project Retrospective",
                _doc(
                    _heading(1, "Project Retrospective"),
                    _paragraph(
                        "Use retrospectives to turn raw work into durable career "
                        "and product knowledge."
                    ),
                ),
                (
                    "Project Retrospective. Use retrospectives to turn raw work into durable "
                    "career and product knowledge."
                ),
            ),
        ]

        page_ids: list[uuid.UUID] = []
        for title, content_json, content_text in pages:
            obj, page = await page_service.create_page(
                db,
                user_id,
                PageCreate(title=title, content_json=content_json),
            )
            obj.tags = [TUTORIAL_TAG]
            await page_service.update_page(
                db,
                page.id,
                user_id,
                PageUpdate(content_text=content_text),
            )
            page_ids.append(page.id)

        _src_obj, _src, _job = await source_service.create_source(
            db,
            user_id,
            SourceCreate(
                source_type="web",
                title="Personal Knowledge Management — Wikipedia",
                description="An overview of PKM techniques used as a tutorial reference.",
                tags=[TUTORIAL_TAG],
                url="https://en.wikipedia.org/wiki/Personal_knowledge_management",
            ),
        )

        project_obj, _project = await project_service.create_project(
            db,
            user_id=user_id,
            payload=ProjectCreate(
                title="KnowledgeOS Demo",
                role="Product Engineer",
                organization="Demo Corp",
                skills=["Python", "TypeScript"],
                tags=[TUTORIAL_TAG],
            ),
        )

        await edge_service.create_edge(
            db,
            page_ids[0],
            page_ids[1],
            kind="related_to",
            user_id=user_id,
        )
        await edge_service.create_edge(
            db,
            page_ids[0],
            project_obj.id,
            kind="related_to",
            user_id=user_id,
        )

        await agent_run_service.complete(
            db,
            run,
            output={
                "seeded": True,
                "tag": TUTORIAL_TAG,
                "object_ids": [str(oid) for oid in [*page_ids, _src_obj.id, project_obj.id]],
            },
        )
    except Exception as exc:
        await agent_run_service.fail(db, run, str(exc))
        raise

    return True


async def reset_tutorial(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Soft-delete tutorial objects for the current user. Returns the number of objects touched."""
    result = await db.execute(
        select(KosObject).where(
            KosObject.user_id == user_id,
            KosObject.deleted_at.is_(None),
            TUTORIAL_TAG == any_(KosObject.tags),
        )
    )
    objects = list(result.scalars().all())
    now = datetime.now(UTC)
    for obj in objects:
        obj.deleted_at = now
        obj.updated_at = now
    await db.flush()
    return len(objects)
