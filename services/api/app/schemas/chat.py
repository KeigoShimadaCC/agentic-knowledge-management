import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChatProvider = Literal["auto", "chatgpt", "claude", "markdown", "plain_text", "unknown"]
ChatRawFormat = Literal["json", "md", "txt"]


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

    model_config = {"from_attributes": True, "populate_by_name": True}


class ChatImportResponse(BaseModel):
    imported: list[ChatOut]
    total: int
