from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_story_record import InterviewStoryRecord
from app.models.object import KosObject
from app.models.project import Project
from app.models.resume_bullet_set import ResumeBulletSet
from app.schemas.career_artifacts import SaveInterviewStoryRequest, SaveResumeBulletSetRequest
from app.services import edge_service
from app.services.audited_write_service import audited_write

if TYPE_CHECKING:
    from redis.asyncio import Redis


ArtifactRow = tuple[KosObject, ResumeBulletSet]
StoryRow = tuple[KosObject, InterviewStoryRecord]


async def save_resume_bullet_set(
    db: AsyncSession,
    redis: "Redis",
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: SaveResumeBulletSetRequest,
    agent_id: str,
) -> ArtifactRow:
    project_obj, _project = await _get_project_or_404(db, user_id=user_id, project_id=project_id)

    async def _do_save(write_db: AsyncSession) -> ArtifactRow:
        obj = KosObject(
            user_id=user_id,
            kind="resume_bullet_set",
            title=f"Bullets · {project_obj.title}",
            description=payload.emphasis,
            ai_generated=True,
        )
        write_db.add(obj)
        await write_db.flush()

        row = ResumeBulletSet(
            id=obj.id,
            project_id=project_id,
            target_role=payload.target_role,
            emphasis=payload.emphasis,
            count=payload.count,
            bullets=[bullet.model_dump(mode="json") for bullet in payload.bullets],
            agent_run_id=payload.agent_run_id,
            prompt_version=payload.prompt_version,
        )
        write_db.add(row)
        await write_db.flush()

        await edge_service.create_edge(
            write_db,
            obj.id,
            project_id,
            "belongs_to_project",
            user_id=user_id,
        )
        for evidence_id in _unique_resume_evidence_ids(payload):
            await edge_service.create_edge(
                write_db,
                obj.id,
                evidence_id,
                "cites",
                user_id=user_id,
            )
        await write_db.flush()
        return obj, row

    return await audited_write(
        db,
        redis,
        user_id=user_id,
        agent_id=agent_id,
        tool_name="save_resume_bullet_set",
        args={"project_id": str(project_id), "count": payload.count},
        fn=_do_save,
    )


async def save_interview_story(
    db: AsyncSession,
    redis: "Redis",
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: SaveInterviewStoryRequest,
    agent_id: str,
) -> StoryRow:
    project_obj, _project = await _get_project_or_404(db, user_id=user_id, project_id=project_id)

    async def _do_save(write_db: AsyncSession) -> StoryRow:
        obj = KosObject(
            user_id=user_id,
            kind="interview_story",
            title=f"Story · {project_obj.title} ({payload.question_type})",
            description=payload.story.result,
            ai_generated=True,
        )
        write_db.add(obj)
        await write_db.flush()

        row = InterviewStoryRecord(
            id=obj.id,
            project_id=project_id,
            question_type=payload.question_type,
            target_role=payload.target_role,
            max_words=payload.max_words,
            word_count=payload.word_count,
            story=payload.story.model_dump(mode="json"),
            agent_run_id=payload.agent_run_id,
            prompt_version=payload.prompt_version,
        )
        write_db.add(row)
        await write_db.flush()

        await edge_service.create_edge(
            write_db,
            obj.id,
            project_id,
            "belongs_to_project",
            user_id=user_id,
        )
        for evidence_id in _unique_story_evidence_ids(payload):
            await edge_service.create_edge(
                write_db,
                obj.id,
                evidence_id,
                "cites",
                user_id=user_id,
            )
        await write_db.flush()
        return obj, row

    return await audited_write(
        db,
        redis,
        user_id=user_id,
        agent_id=agent_id,
        tool_name="save_interview_story",
        args={"project_id": str(project_id), "question_type": payload.question_type},
        fn=_do_save,
    )


async def list_resume_bullet_sets(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[ArtifactRow]:
    await _get_project_or_404(db, user_id=user_id, project_id=project_id)
    stmt = (
        select(KosObject, ResumeBulletSet)
        .join(ResumeBulletSet, ResumeBulletSet.id == KosObject.id)
        .where(
            KosObject.user_id == user_id,
            KosObject.kind == "resume_bullet_set",
            KosObject.deleted_at.is_(None),
            ResumeBulletSet.project_id == project_id,
        )
        .order_by(ResumeBulletSet.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [(r[0], r[1]) for r in rows]


async def get_resume_bullet_set(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    bullet_set_id: uuid.UUID,
) -> ArtifactRow | None:
    stmt = (
        select(KosObject, ResumeBulletSet)
        .join(ResumeBulletSet, ResumeBulletSet.id == KosObject.id)
        .where(
            KosObject.id == bullet_set_id,
            KosObject.user_id == user_id,
            KosObject.kind == "resume_bullet_set",
            KosObject.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        return None
    return row[0], row[1]


async def delete_resume_bullet_set(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    bullet_set_id: uuid.UUID,
) -> bool:
    row = await get_resume_bullet_set(db, user_id=user_id, bullet_set_id=bullet_set_id)
    if not row:
        return False
    obj, _artifact = row
    obj.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def list_interview_stories(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    question_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[StoryRow]:
    await _get_project_or_404(db, user_id=user_id, project_id=project_id)
    stmt = (
        select(KosObject, InterviewStoryRecord)
        .join(InterviewStoryRecord, InterviewStoryRecord.id == KosObject.id)
        .where(
            KosObject.user_id == user_id,
            KosObject.kind == "interview_story",
            KosObject.deleted_at.is_(None),
            InterviewStoryRecord.project_id == project_id,
        )
        .order_by(InterviewStoryRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if question_type:
        stmt = stmt.where(InterviewStoryRecord.question_type == question_type)
    rows = (await db.execute(stmt)).all()
    return [(r[0], r[1]) for r in rows]


async def get_interview_story(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    story_id: uuid.UUID,
) -> StoryRow | None:
    stmt = (
        select(KosObject, InterviewStoryRecord)
        .join(InterviewStoryRecord, InterviewStoryRecord.id == KosObject.id)
        .where(
            KosObject.id == story_id,
            KosObject.user_id == user_id,
            KosObject.kind == "interview_story",
            KosObject.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        return None
    return row[0], row[1]


async def delete_interview_story(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    story_id: uuid.UUID,
) -> bool:
    row = await get_interview_story(db, user_id=user_id, story_id=story_id)
    if not row:
        return False
    obj, _story = row
    obj.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def _get_project_or_404(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> tuple[KosObject, Project]:
    stmt = (
        select(KosObject, Project)
        .join(Project, Project.id == KosObject.id)
        .where(
            KosObject.id == project_id,
            KosObject.user_id == user_id,
            KosObject.kind == "project",
            KosObject.deleted_at.is_(None),
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return row[0], row[1]


def _unique_resume_evidence_ids(payload: SaveResumeBulletSetRequest) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for bullet in payload.bullets:
        for evidence_id in bullet.evidence_object_ids:
            if evidence_id not in seen:
                seen.add(evidence_id)
                ordered.append(evidence_id)
    return ordered


def _unique_story_evidence_ids(payload: SaveInterviewStoryRequest) -> list[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for evidence_id in payload.story.evidence_object_ids:
        if evidence_id not in seen:
            seen.add(evidence_id)
            ordered.append(evidence_id)
    return ordered
