import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator

SourceType = Literal["pdf", "image", "video", "audio", "youtube", "web", "csv", "file"]

FILE_SOURCE_TYPES = {"pdf", "image", "video", "audio", "csv", "file"}
URL_SOURCE_TYPES = {"youtube", "web"}


class SourceCreate(BaseModel):
    source_type: SourceType
    title: str = ""
    description: str | None = None
    tags: list[str] = []
    url: str | None = None
    asset_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_source_location(self) -> "SourceCreate":
        if self.source_type in FILE_SOURCE_TYPES and self.asset_id is None:
            raise ValueError("asset_id is required for file-backed sources")
        if self.source_type in URL_SOURCE_TYPES and self.url is None:
            raise ValueError("url is required for URL-backed sources")
        return self


class SourceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class SourceOut(BaseModel):
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
    source_type: str
    url: str | None
    asset_id: uuid.UUID | None
    ingestion_status: str
    extracted_text: str | None
    page_count: int | None
    thumbnail_path: str | None
    preview_data: dict | None
    error_message: str | None

    model_config = {"from_attributes": True}
