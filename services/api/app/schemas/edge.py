import uuid
from datetime import datetime

from pydantic import BaseModel


class EdgeCreate(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    kind: str


class EdgeOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    kind: str
    weight: float
    metadata_: dict
    created_at: datetime
    deleted_at: datetime | None

    model_config = {"from_attributes": True}
