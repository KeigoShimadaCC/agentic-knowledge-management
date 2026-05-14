import uuid
from datetime import datetime

from pydantic import BaseModel


class AssetOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_path: str
    status: str
    width: int | None
    height: int | None
    duration_secs: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetUploadResponse(BaseModel):
    object: "ObjectOut"
    asset: AssetOut


from app.schemas.object import ObjectOut  # noqa: E402 — circular import workaround

AssetUploadResponse.model_rebuild()
