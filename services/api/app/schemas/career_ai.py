from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BulletConfidence = Literal["high", "medium", "low"]
InterviewQuestionType = Literal["behavioral", "technical", "leadership"]


class GenerateResumeBulletsRequest(BaseModel):
    project_id: UUID
    target_role: str | None = Field(None, max_length=255)
    emphasis: str | None = Field(None, max_length=500)
    count: int = Field(3, ge=1, le=5)
    max_evidence_objects: int = Field(10, ge=1, le=20)


class ResumeBullet(BaseModel):
    text: str = Field(min_length=1)
    evidence_object_ids: list[UUID] = Field(default_factory=list)
    confidence: BulletConfidence = "medium"
    metrics_cited: list[str] = Field(default_factory=list)


class GenerateResumeBulletsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    project_id: UUID
    bullets: list[ResumeBullet]
    agent_run_id: UUID
    evidence_count: int


class GenerateInterviewStoryRequest(BaseModel):
    project_id: UUID
    question_type: InterviewQuestionType = "behavioral"
    target_role: str | None = Field(None, max_length=255)
    max_words: int = Field(400, ge=100, le=800)
    max_evidence_objects: int = Field(10, ge=1, le=20)


class StarStory(BaseModel):
    situation: str = Field(min_length=1)
    task: str = Field(min_length=1)
    action: str = Field(min_length=1)
    result: str = Field(min_length=1)
    evidence_object_ids: list[UUID] = Field(default_factory=list)


class GenerateInterviewStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    project_id: UUID
    story: StarStory
    agent_run_id: UUID
    word_count: int
