import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ChatProvider = Literal["auto", "chatgpt", "claude", "markdown", "plain_text", "unknown"]
ChatRawFormat = Literal["json", "md", "txt"]
Confidence = Literal["low", "medium", "high"]
ClaimType = Literal["fact", "hypothesis", "preference", "decision_context", "unknown"]
ConceptType = Literal[
    "person",
    "organization",
    "product",
    "technology",
    "topic",
    "project",
    "unknown",
]
StructuredSummaryStatus = Literal["none", "previewed", "applied", "failed"]
StructuredEdgeKind = Literal[
    "related_to",
    "mentions",
    "supports",
    "contradicts",
    "belongs_to_project",
    "created_from",
]


class ChatImportJson(BaseModel):
    content: str
    provider: ChatProvider = "auto"
    title: str | None = None
    raw_format: ChatRawFormat | None = None


class ChatTurnOut(BaseModel):
    turn_index: int
    role: str
    author: str | None = None
    content: str
    created_at: str | None = None
    metadata: dict = Field(default_factory=dict)


class ChatSummaryDateRange(BaseModel):
    start: str | None = None
    end: str | None = None

    model_config = {"extra": "forbid"}


class TurnReferencedItem(BaseModel):
    turn_refs: list[int] = Field(default_factory=list)
    confidence: Confidence = "medium"

    @field_validator("turn_refs")
    @classmethod
    def validate_turn_refs(cls, value: list[int]) -> list[int]:
        if any(ref < 0 for ref in value):
            raise ValueError("turn_refs must contain non-negative turn indexes")
        return sorted(set(value))

    model_config = {"extra": "forbid"}


class KeyDecision(TurnReferencedItem):
    decision: str
    rationale: str | None = None


class OpenQuestion(TurnReferencedItem):
    question: str
    status: str = "open"


class ActionItem(TurnReferencedItem):
    task: str
    owner: str | None = None
    due_at: str | None = None


class ExtractedClaim(TurnReferencedItem):
    claim: str
    type: ClaimType = "unknown"


class ExtractedConcept(TurnReferencedItem):
    name: str
    type: ConceptType = "unknown"


class SuggestedLink(BaseModel):
    target_object_id: uuid.UUID | None = None
    target_title: str
    edge_kind: StructuredEdgeKind
    rationale: str
    confidence: Confidence = "medium"

    model_config = {"extra": "forbid"}


class StructuredChatSummary(BaseModel):
    title: str
    summary: str
    date_range: ChatSummaryDateRange = Field(default_factory=ChatSummaryDateRange)
    topics: list[str] = Field(default_factory=list)
    key_decisions: list[KeyDecision] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)
    concepts: list[ExtractedConcept] = Field(default_factory=list)
    suggested_links: list[SuggestedLink] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class StructuredSummaryPreviewOut(BaseModel):
    structured_summary: StructuredChatSummary
    agent_run_id: uuid.UUID
    status: StructuredSummaryStatus


class StructuredSummaryApplyIn(BaseModel):
    structured_summary: StructuredChatSummary | None = None
    create_claims: bool = True
    create_tasks: bool = True
    create_concepts: bool = False
    link_existing_objects: bool = True


class ChatOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    kind: str
    title: str
    description: str | None
    tags: list[str]
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    provider: str
    external_chat_id: str | None
    source_filename: str | None
    raw_storage_path: str
    raw_format: str
    turn_count: int
    started_at: datetime | None
    ended_at: datetime | None
    imported_at: datetime
    parsed_turns: list[ChatTurnOut]
    content_text: str
    metadata: dict = Field(alias="metadata_", serialization_alias="metadata")
    structured_summary: dict | None = None
    structured_summary_status: str = "none"
    structured_summary_agent_run_id: uuid.UUID | None = None
    structured_summary_updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class StructuredSummaryApplyOut(BaseModel):
    chat: ChatOut
    created_objects: list[dict] = Field(default_factory=list)
    reused_objects: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class ChatImportResponse(BaseModel):
    imported: list[ChatOut]
    total: int
