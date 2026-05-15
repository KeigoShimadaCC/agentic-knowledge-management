from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProjectStatus = Literal["active", "paused", "completed", "archived"]
ProjectConfidence = Literal["manual", "ai_extracted", "verified"]


def _normalize_skills(value: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in value:
        t = s.strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _validate_metrics_primitive(m: dict[str, Any]) -> dict[str, Any]:
    for k, v in m.items():
        if not isinstance(k, str):
            raise ValueError("metrics keys must be strings")
        if v is not None and not isinstance(v, str | int | float | bool):
            raise ValueError("metrics values must be string, number, bool, or null")
    return m


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    role: str | None = Field(None, max_length=255)
    organization: str | None = Field(None, max_length=255)
    problem: str | None = None
    actions: str | None = None
    results: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    status: ProjectStatus = "active"

    @field_validator("skills", mode="before")
    @classmethod
    def skills_normalize(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise TypeError("skills must be a list of strings")
        return _normalize_skills([str(x) for x in v])

    @field_validator("metrics", mode="before")
    @classmethod
    def metrics_primitive(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise TypeError("metrics must be an object")
        return _validate_metrics_primitive(dict(v))

    @model_validator(mode="after")
    def period_order(self) -> ProjectBase:
        if self.period_start is not None and self.period_end is not None:
            if self.period_end < self.period_start:
                raise ValueError("period_end must be >= period_start")
        return self


class ProjectCreate(ProjectBase):
    tags: list[str] = Field(default_factory=list)
    extracted_from: UUID | None = None
    confidence: ProjectConfidence = "manual"


class ProjectUpdate(BaseModel):
    """All fields optional — PATCH semantics."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    role: str | None = Field(None, max_length=255)
    organization: str | None = Field(None, max_length=255)
    problem: str | None = None
    actions: str | None = None
    results: str | None = None
    metrics: dict[str, Any] | None = None
    skills: list[str] | None = None
    status: ProjectStatus | None = None
    tags: list[str] | None = None
    confidence: ProjectConfidence | None = None

    @field_validator("skills", mode="before")
    @classmethod
    def skills_normalize_optional(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise TypeError("skills must be a list of strings")
        return _normalize_skills([str(x) for x in v])

    @field_validator("metrics", mode="before")
    @classmethod
    def metrics_primitive_optional(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise TypeError("metrics must be an object")
        return _validate_metrics_primitive(dict(v))

    @model_validator(mode="after")
    def period_order_partial(self) -> ProjectUpdate:
        if self.period_start is not None and self.period_end is not None:
            if self.period_end < self.period_start:
                raise ValueError("period_end must be >= period_start")
        return self


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tags: list[str]
    is_pinned: bool
    is_archived: bool
    confidence: ProjectConfidence
    extracted_from: UUID | None
    extracted_by_agent_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# --- AI extract-project (Phase 9A) ---


class ExtractProjectRequest(BaseModel):
    source_id: UUID
    create: bool = True
    period_hint: tuple[date | None, date | None] | None = None


class ExtractedProjectDraft(BaseModel):
    title: str
    description: str | None
    period_start: date | None
    period_end: date | None
    role: str | None
    organization: str | None
    problem: str | None
    actions: str | None
    results: str | None
    metrics: dict[str, Any]
    skills: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)


class ExtractProjectResponse(BaseModel):
    draft: ExtractedProjectDraft
    project_id: UUID | None
    agent_run_id: UUID
    source_id: UUID


def normalize_skills_for_draft(skills: list[str]) -> list[str]:
    """Post-parse normalization: lowercase, strip, dedupe, cap 12."""
    base = _normalize_skills(skills)
    return base[:12]


def draft_metrics_from_parsed(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("metrics") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if v is None or isinstance(v, str | int | float | bool):
            out[k] = v
    return out


def parse_extract_project_json(raw: str) -> dict[str, Any]:
    return json.loads(raw)
