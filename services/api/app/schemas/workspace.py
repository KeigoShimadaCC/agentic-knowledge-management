from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PaneKind = Literal["page", "source", "asset", "chat", "project"]
PaneMode = Literal["read", "edit"]
WorkspaceSplit = Literal["horizontal", "vertical"]


class WorkspacePane(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    object_id: UUID | None = None
    object_kind: PaneKind | None = None
    size_pct: int = Field(..., ge=5, le=100)
    mode: PaneMode = "read"


class WorkspaceLayout(BaseModel):
    version: Literal[1] = 1
    split: WorkspaceSplit | None = None
    panes: list[WorkspacePane] = Field(..., min_length=1, max_length=4)
    active_pane_id: str

    @model_validator(mode="before")
    @classmethod
    def require_split_for_multi_pane(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        panes = data.get("panes")
        if isinstance(panes, list) and len(panes) >= 2 and data.get("split") is None:
            raise ValueError("split is required when a workspace has multiple panes")
        return data

    @model_validator(mode="after")
    def validate_layout(self) -> "WorkspaceLayout":
        pane_ids = [pane.id for pane in self.panes]
        if len(pane_ids) != len(set(pane_ids)):
            raise ValueError("pane ids must be unique within a workspace")
        if self.active_pane_id not in pane_ids:
            raise ValueError("active_pane_id must reference an existing pane")
        if len(self.panes) >= 2 and any(pane.size_pct > 95 for pane in self.panes):
            raise ValueError("pane size_pct must be between 5 and 95 for multi-pane layouts")
        total_size = sum(pane.size_pct for pane in self.panes)
        if not 98 <= total_size <= 102:
            raise ValueError(f"pane size_pct must sum to ~100, got {total_size}")
        return self


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    layout: WorkspaceLayout
    is_pinned: bool = False


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    layout: WorkspaceLayout | None = None
    is_pinned: bool | None = None


class WorkspaceOut(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
