from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResponse,
    VectorSearchRequest,
)
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/keyword", response_model=SearchResponse)
async def keyword_search(
    q: str = Query(..., min_length=1),
    kind: str | None = Query(None),
    source_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    results = await search_service.keyword_search(
        db, user.id, q, kind=kind, source_type=source_type, limit=limit, offset=offset
    )
    return SearchResponse(results=results, total=len(results), query=q, mode="keyword")


@router.post("/vector", response_model=SearchResponse)
async def vector_search(
    body: VectorSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    from app.search.embedding import get_embedding_provider

    provider = get_embedding_provider()
    if not provider.is_enabled:
        raise HTTPException(status_code=503, detail="embeddings_disabled")

    results = await search_service.vector_search(
        db,
        user.id,
        body.q,
        kind=body.kind,
        source_type=body.source_type,
        limit=body.limit,
        score_threshold=body.score_threshold,
    )
    return SearchResponse(results=results, total=len(results), query=body.q, mode="vector")


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    body: HybridSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HybridSearchResponse:
    results, embeddings_used = await search_service.hybrid_search(
        db,
        user.id,
        body.q,
        kind=body.kind,
        source_type=body.source_type,
        limit=body.limit,
    )
    return HybridSearchResponse(
        results=results,
        total=len(results),
        query=body.q,
        embeddings_used=embeddings_used,
    )
