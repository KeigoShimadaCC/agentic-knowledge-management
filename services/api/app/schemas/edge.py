import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.edge_kinds import validate_edge_kind

EdgeDirection = Literal["incoming", "outgoing", "both"]


class EdgeCreate(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    kind: str
    weight: float = 1.0
    metadata_: dict = Field(default_factory=dict, alias="metadata")

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        return validate_edge_kind(value)

    model_config = {"populate_by_name": True}


class ObjectSummary(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    description: str | None
    tags: list[str]
    deleted_at: datetime | None

    model_config = {"from_attributes": True}


class EdgeOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    kind: str
    weight: float
    metadata: dict = Field(alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    deleted_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class EdgeWithObjectsOut(EdgeOut):
    source: ObjectSummary
    target: ObjectSummary
    direction: Literal["incoming", "outgoing"] | None = None


class RelatedObjectOut(BaseModel):
    object: ObjectSummary
    distance: int
    score: float
    via_edges: list[EdgeWithObjectsOut]
