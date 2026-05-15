from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.common import PaginatedResponse
from app.schemas.object import ObjectOut
from app.schemas.project import ExtractProjectRequest, ExtractProjectResponse
from app.services import ai_service, project_service

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
    return await ai_service.answer_question(db, user.id, body.q, body.kind, body.limit)


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
