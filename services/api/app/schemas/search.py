from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SearchSnippet(BaseModel):
    """Plain-text snippet with character ranges marking highlighted terms."""

    text: str
    highlights: list[tuple[int, int]] = []


class SearchResult(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    snippet: SearchSnippet | None = None
    tags: list[str] = []
    score: float
    updated_at: datetime
    source_type: str | None = None
    ingestion_status: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
    mode: str


class VectorSearchRequest(BaseModel):
    q: str
    kind: str | None = None
    source_type: str | None = None
    limit: int = 20
    score_threshold: float | None = None


class HybridSearchRequest(BaseModel):
    q: str
    kind: str | None = None
    source_type: str | None = None
    limit: int = 20
    debug: bool = False


class HybridSearchResult(SearchResult):
    keyword_score: float = 0.0
    vector_score: float = 0.0
    recency_boost: float = 0.0


class HybridSearchResponse(BaseModel):
    results: list[HybridSearchResult]
    total: int
    query: str
    mode: str = "hybrid"
    embeddings_used: bool = True
