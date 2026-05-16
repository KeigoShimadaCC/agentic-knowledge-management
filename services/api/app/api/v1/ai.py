from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import call_ai
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.object import KosObject
from app.models.user import User
from app.schemas.ai import (
    AnswerRequest,
    AnswerResponse,
    ExtractRequest,
    ExtractResponse,
    SuggestLinksRequest,
    SuggestLinksResponse,
    SummarizeRequest,
    SummarizeResponse,
    TriageRequest,
    TriageResponse,
)
from app.schemas.career_ai import (
    GenerateInterviewStoryRequest,
    GenerateInterviewStoryResponse,
    GenerateResumeBulletsRequest,
    GenerateResumeBulletsResponse,
)
from app.schemas.common import PaginatedResponse
from app.schemas.inline_ai import (
    AiCompleteRequest,
    AiCompleteResponse,
    AiTransformRequest,
    AiTransformResponse,
)
from app.schemas.object import ObjectOut
from app.schemas.project import ExtractProjectRequest, ExtractProjectResponse
from app.services import ai_service, career_ai_service, project_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    body: SummarizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SummarizeResponse:
    return await ai_service.summarize_object(db, user.id, body.object_id, body.force)


@router.post("/extract-claims", response_model=ExtractResponse)
async def extract_claims(
    body: ExtractRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractResponse:
    return await ai_service.extract_claims(db, user.id, body.object_id)


@router.post("/extract-tasks", response_model=ExtractResponse)
async def extract_tasks(
    body: ExtractRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractResponse:
    return await ai_service.extract_tasks(db, user.id, body.object_id)


@router.post("/suggest-links", response_model=SuggestLinksResponse)
async def suggest_links(
    body: SuggestLinksRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuggestLinksResponse:
    return await ai_service.suggest_links(db, user.id, body.object_id, body.limit)


@router.post("/answer", response_model=AnswerResponse)
async def answer(
    body: AnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerResponse:
    return await ai_service.answer_question(
        db, user.id, body.q, body.kind, body.limit, body.object_ids
    )


@router.post("/triage", response_model=TriageResponse)
async def triage(
    body: TriageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TriageResponse:
    return await ai_service.triage_object(db, user.id, body.object_id)


@router.get("/inbox", response_model=PaginatedResponse[ObjectOut])
async def inbox(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ObjectOut]:
    cutoff = datetime.now(UTC) - timedelta(days=30)
    base_q = (
        select(KosObject)
        .where(
            KosObject.user_id == user.id,
            KosObject.deleted_at.is_(None),
            or_(KosObject.tags == [], KosObject.tags.is_(None)),
            or_(KosObject.description.is_(None), KosObject.description == ""),
            KosObject.created_at > cutoff,
        )
        .order_by(KosObject.created_at.desc())
    )

    total_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_result.scalar() or 0

    rows = await db.execute(base_q.offset(offset).limit(limit))
    objects = rows.scalars().all()

    items = [ObjectOut.model_validate(o) for o in objects]
    pages = (total + limit - 1) // limit if total else 0
    return PaginatedResponse(
        items=items, total=total, page=offset // limit + 1, limit=limit, pages=pages
    )


@router.post("/extract-project", response_model=ExtractProjectResponse)
async def extract_project_endpoint(
    body: ExtractProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractProjectResponse:
    result = await project_service.extract_project(db, user_id=user.id, payload=body)
    await db.commit()
    return result


@router.post("/generate-resume-bullets", response_model=GenerateResumeBulletsResponse)
async def generate_resume_bullets_endpoint(
    body: GenerateResumeBulletsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResumeBulletsResponse:
    result = await career_ai_service.generate_resume_bullets(db, user_id=user.id, payload=body)
    await db.commit()
    return result


@router.post("/generate-interview-story", response_model=GenerateInterviewStoryResponse)
async def generate_interview_story_endpoint(
    body: GenerateInterviewStoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateInterviewStoryResponse:
    result = await career_ai_service.generate_interview_story(db, user_id=user.id, payload=body)
    await db.commit()
    return result


_COMPLETE_SYSTEM: dict[str, str] = {
    "continue": (
        "You are a writing assistant. Continue the text naturally."
        " Return only the continuation, no preamble."
    ),
    "expand": (
        "You are a writing assistant. Expand the text with more detail."
        " Return only the expanded continuation."
    ),
}

_TRANSFORM_SYSTEM: dict[str, str] = {
    "improve": (
        "You are an editor. Improve the clarity and flow of the text."
        " Return only the improved version."
    ),
    "concise": (
        "You are an editor. Make the text more concise without losing meaning."
        " Return only the revised version."
    ),
    "grammar": (
        "You are a proofreader. Fix all grammar and spelling errors."
        " Return only the corrected version."
    ),
    "summarize": (
        "You are an editor. Write a one-paragraph summary of the text. Return only the summary."
    ),
}


@router.post("/complete", response_model=AiCompleteResponse)
async def ai_complete(
    body: AiCompleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiCompleteResponse:
    system = _COMPLETE_SYSTEM[body.instruction]
    user_msg = body.context_before
    if body.context_after:
        user_msg += f"\n[TEXT AFTER CURSOR: {body.context_after}]"
    text, run = await call_ai(
        db,
        user_id=user.id,
        agent_type="inline_ai_complete",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        input_context={"instruction": body.instruction, "object_id": str(body.object_id)},
    )
    await db.commit()
    return AiCompleteResponse(completion=text, agent_run_id=run.id)


@router.post("/transform", response_model=AiTransformResponse)
async def ai_transform(
    body: AiTransformRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiTransformResponse:
    system = _TRANSFORM_SYSTEM[body.instruction]
    text, run = await call_ai(
        db,
        user_id=user.id,
        agent_type="inline_ai_transform",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": body.text},
        ],
        input_context={"instruction": body.instruction, "object_id": str(body.object_id)},
    )
    await db.commit()
    return AiTransformResponse(result=text, agent_run_id=run.id)
