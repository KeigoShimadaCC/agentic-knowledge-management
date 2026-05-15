from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import agent_id_from_request, get_redis
from app.db.session import get_db
from app.models.interview_story_record import InterviewStoryRecord
from app.models.object import KosObject
from app.models.resume_bullet_set import ResumeBulletSet
from app.models.user import User
from app.schemas.career_ai import InterviewQuestionType
from app.schemas.career_artifacts import (
    InterviewStoryOut,
    ResumeBulletSetOut,
    SaveInterviewStoryRequest,
    SaveResumeBulletSetRequest,
)
from app.services import career_artifact_service, reindex_service

router = APIRouter(tags=["career-artifacts"])


def _build_resume_bullet_set_out(obj: KosObject, row: ResumeBulletSet) -> ResumeBulletSetOut:
    return ResumeBulletSetOut(
        id=obj.id,
        user_id=obj.user_id,
        project_id=row.project_id,
        target_role=row.target_role,
        emphasis=row.emphasis,
        count=row.count,
        bullets=list(row.bullets or []),
        agent_run_id=row.agent_run_id,
        prompt_version=row.prompt_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=obj.deleted_at,
    )


def _build_interview_story_out(obj: KosObject, row: InterviewStoryRecord) -> InterviewStoryOut:
    return InterviewStoryOut(
        id=obj.id,
        user_id=obj.user_id,
        project_id=row.project_id,
        question_type=row.question_type,
        target_role=row.target_role,
        max_words=row.max_words,
        word_count=row.word_count,
        story=dict(row.story or {}),
        agent_run_id=row.agent_run_id,
        prompt_version=row.prompt_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=obj.deleted_at,
    )


@router.post(
    "/projects/{project_id}/resume-bullet-sets",
    response_model=ResumeBulletSetOut,
    status_code=201,
)
async def save_resume_bullet_set_endpoint(
    project_id: uuid.UUID,
    payload: SaveResumeBulletSetRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ResumeBulletSetOut:
    obj, row = await career_artifact_service.save_resume_bullet_set(
        db,
        redis,
        user_id=user.id,
        project_id=project_id,
        payload=payload,
        agent_id=agent_id_from_request(request),
    )
    await db.commit()
    reindex_service.enqueue_reindex_object(obj.id)
    await db.refresh(obj)
    await db.refresh(row)
    return _build_resume_bullet_set_out(obj, row)


@router.get(
    "/projects/{project_id}/resume-bullet-sets",
    response_model=list[ResumeBulletSetOut],
)
async def list_resume_bullet_sets_endpoint(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeBulletSetOut]:
    rows = await career_artifact_service.list_resume_bullet_sets(
        db,
        user_id=user.id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return [_build_resume_bullet_set_out(obj, row) for obj, row in rows]


@router.get("/resume-bullet-sets/{bullet_set_id}", response_model=ResumeBulletSetOut)
async def get_resume_bullet_set_endpoint(
    bullet_set_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeBulletSetOut:
    row = await career_artifact_service.get_resume_bullet_set(
        db,
        user_id=user.id,
        bullet_set_id=bullet_set_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Resume bullet set not found")
    obj, artifact = row
    return _build_resume_bullet_set_out(obj, artifact)


@router.delete("/resume-bullet-sets/{bullet_set_id}", status_code=204)
async def delete_resume_bullet_set_endpoint(
    bullet_set_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await career_artifact_service.delete_resume_bullet_set(
        db,
        user_id=user.id,
        bullet_set_id=bullet_set_id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Resume bullet set not found")
    await db.commit()


@router.post(
    "/projects/{project_id}/interview-stories",
    response_model=InterviewStoryOut,
    status_code=201,
)
async def save_interview_story_endpoint(
    project_id: uuid.UUID,
    payload: SaveInterviewStoryRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> InterviewStoryOut:
    obj, row = await career_artifact_service.save_interview_story(
        db,
        redis,
        user_id=user.id,
        project_id=project_id,
        payload=payload,
        agent_id=agent_id_from_request(request),
    )
    await db.commit()
    reindex_service.enqueue_reindex_object(obj.id)
    await db.refresh(obj)
    await db.refresh(row)
    return _build_interview_story_out(obj, row)


@router.get(
    "/projects/{project_id}/interview-stories",
    response_model=list[InterviewStoryOut],
)
async def list_interview_stories_endpoint(
    project_id: uuid.UUID,
    question_type: InterviewQuestionType | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InterviewStoryOut]:
    rows = await career_artifact_service.list_interview_stories(
        db,
        user_id=user.id,
        project_id=project_id,
        question_type=question_type,
        limit=limit,
        offset=offset,
    )
    return [_build_interview_story_out(obj, row) for obj, row in rows]


@router.get("/interview-stories/{story_id}", response_model=InterviewStoryOut)
async def get_interview_story_endpoint(
    story_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewStoryOut:
    row = await career_artifact_service.get_interview_story(
        db,
        user_id=user.id,
        story_id=story_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Interview story not found")
    obj, story = row
    return _build_interview_story_out(obj, story)


@router.delete("/interview-stories/{story_id}", status_code=204)
async def delete_interview_story_endpoint(
    story_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await career_artifact_service.delete_interview_story(
        db,
        user_id=user.id,
        story_id=story_id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Interview story not found")
    await db.commit()
