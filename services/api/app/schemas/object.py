import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ObjectCreate(BaseModel):
    kind: str = Field(pattern="^(page|asset|note|bookmark|collection)$")
    title: str = ""
    description: str | None = None
    tags: list[str] = []
    metadata_: dict = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class ObjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    metadata_: dict | None = Field(default=None, alias="metadata")
    is_pinned: bool | None = None
    is_archived: bool | None = None

    model_config = {"populate_by_name": True}


class ObjectOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    kind: str
    title: str
    description: str | None
    tags: list[str]
    metadata: dict = Field(alias="metadata_", serialization_alias="metadata")
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = {"from_attributes": True, "populate_by_name": True}
