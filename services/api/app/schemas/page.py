import uuid
from datetime import datetime

from pydantic import BaseModel


class PageCreate(BaseModel):
    title: str = ""
    content_json: dict = {}


class PageUpdate(BaseModel):
    title: str | None = None
    content_json: dict | None = None
    content_text: str | None = None
    expected_version: int | None = None


class PageOut(BaseModel):
    id: uuid.UUID
    content_json: dict
    content_text: str
    word_count: int
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
