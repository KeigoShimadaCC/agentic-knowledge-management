from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

CompletionInstruction = Literal["continue", "expand"]
TransformInstruction = Literal["improve", "concise", "grammar", "summarize"]


class AiCompleteRequest(BaseModel):
    context_before: str = Field(..., max_length=4000)
    context_after: str = Field("", max_length=1000)
    instruction: CompletionInstruction = "continue"
    object_id: uuid.UUID | None = None
    max_tokens: int = Field(200, ge=50, le=500)


class AiCompleteResponse(BaseModel):
    completion: str
    agent_run_id: uuid.UUID


class AiTransformRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    instruction: TransformInstruction
    object_id: uuid.UUID | None = None


class AiTransformResponse(BaseModel):
    result: str
    agent_run_id: uuid.UUID
