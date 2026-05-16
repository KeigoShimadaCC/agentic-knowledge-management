import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class McpConnectionTransport(str, Enum):
    stdio = "stdio"
    sse = "sse"


class McpToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict = {}


class McpConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    transport: McpConnectionTransport
    command: str | None = None
    args: list[str] = []
    url: str | None = None
    env_vars: dict[str, str] = {}
    enabled: bool = True


class McpConnectionUpdate(BaseModel):
    name: str | None = None
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env_vars: dict[str, str] | None = None
    enabled: bool | None = None


class McpConnectionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    transport: McpConnectionTransport
    command: str | None
    args: list[str]
    url: str | None
    env_vars: dict[str, str]
    capabilities: list[McpToolDefinition] | None
    enabled: bool
    last_tested_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class McpConnectionTestResult(BaseModel):
    ok: bool
    tools: list[McpToolDefinition]
    error: str | None = None


class McpCallRequest(BaseModel):
    tool_name: str
    args: dict = {}


class McpCallResponse(BaseModel):
    result: dict
    connection_name: str


class McpIngestRequest(BaseModel):
    tool_name: str
    args: dict = {}
    target_kind: str = "source"
    tags: list[str] = []


class McpIngestResponse(BaseModel):
    job_id: str
    status: str
