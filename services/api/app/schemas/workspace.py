from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PaneKind = Literal["page", "source", "asset", "chat", "project"]
PaneMode = Literal["read", "edit"]
WorkspaceSplit = Literal["horizontal", "vertical"]


class WorkspacePane(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    object_id: UUID | None = None
    object_kind: PaneKind | None = None
    size_pct: int = Field(..., ge=5, le=95)
    mode: PaneMode = "read"


class WorkspaceLayout(BaseModel):
    version: Literal[1] = 1
    split: WorkspaceSplit = "horizontal"
    panes: list[WorkspacePane] = Field(..., min_length=1, max_length=4)
    active_pane_id: str

    @model_validator(mode="after")
    def validate_layout(self) -> "WorkspaceLayout":
        pane_ids = [pane.id for pane in self.panes]
        if len(pane_ids) != len(set(pane_ids)):
            raise ValueError("pane ids must be unique within a workspace")
        if self.active_pane_id not in pane_ids:
            raise ValueError("active_pane_id must reference an existing pane")
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
