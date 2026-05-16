from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    object_id: uuid.UUID
    force: bool = False


class SummarizeResponse(BaseModel):
    summary: str
    agent_run_id: uuid.UUID
    cached: bool = False


class ExtractRequest(BaseModel):
    object_id: uuid.UUID


class ExtractedItem(BaseModel):
    id: uuid.UUID
    title: str


class ExtractResponse(BaseModel):
    items: list[ExtractedItem]
    agent_run_id: uuid.UUID


class SuggestLinksRequest(BaseModel):
    object_id: uuid.UUID
    limit: int = Field(default=5, ge=1, le=20)


class LinkSuggestion(BaseModel):
    target_id: uuid.UUID
    target_title: str
    target_kind: str
    reason: str
    confidence: float


class SuggestLinksResponse(BaseModel):
    suggestions: list[LinkSuggestion]
    agent_run_id: uuid.UUID


class AnswerRequest(BaseModel):
    q: str
    kind: str | None = None
    limit: int = Field(default=10, ge=1, le=50)
    object_ids: list[uuid.UUID] | None = None
    use_web_search: bool = False


class Citation(BaseModel):
    object_id: uuid.UUID
    title: str
    kind: str
    snippet: str | None = None


class WebCitation(BaseModel):
    title: str
    url: str
    snippet: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    agent_run_id: uuid.UUID
    context_count: int
    web_citations: list[WebCitation] = []
    warning: str | None = None


class TriageRequest(BaseModel):
    object_id: uuid.UUID


class TriageResponse(BaseModel):
    suggested_tags: list[str]
    suggested_title: str | None = None
    summary: str
    agent_run_id: uuid.UUID


class EnrichPageRequest(BaseModel):
    page_id: uuid.UUID
    query: str


class EnrichPageResponse(BaseModel):
    sources_created: list[uuid.UUID]
    edges_created: list[uuid.UUID]
    agent_run_id: uuid.UUID
