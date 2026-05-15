from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.career_ai import InterviewQuestionType, ResumeBullet, StarStory


class SaveResumeBulletSetRequest(BaseModel):
    target_role: str | None = Field(None, max_length=255)
    emphasis: str | None = Field(None, max_length=500)
    count: int = Field(..., ge=1, le=5)
    bullets: list[ResumeBullet]
    agent_run_id: UUID | None = None
    prompt_version: str | None = None


class ResumeBulletSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    project_id: UUID
    target_role: str | None
    emphasis: str | None
    count: int
    bullets: list[dict]
    agent_run_id: UUID | None
    prompt_version: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SaveInterviewStoryRequest(BaseModel):
    question_type: InterviewQuestionType = "behavioral"
    target_role: str | None = Field(None, max_length=255)
    max_words: int = Field(..., ge=100, le=800)
    word_count: int = Field(..., ge=0)
    story: StarStory
    agent_run_id: UUID | None = None
    prompt_version: str | None = None


class InterviewStoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    project_id: UUID
    question_type: str
    target_role: str | None
    max_words: int
    word_count: int
    story: dict
    agent_run_id: UUID | None
    prompt_version: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
