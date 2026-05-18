from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ProviderName = Literal["openai", "anthropic"]


class SecretStatus(BaseModel):
    key: str
    configured: bool
    source: Literal["runtime", "env", "none"]
    redacted: str | None = None
    last_test_status: str | None = None
    last_test_error: str | None = None
    last_tested_at: datetime | None = None


class AiFeatureSettingOut(BaseModel):
    feature_key: str
    display_name: str
    enabled: bool = True
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    effort: str | None = None
    resolved_provider: str | None = None
    resolved_model: str | None = None
    resolved_temperature: float | None = None
    resolved_max_tokens: int | None = None
    supports_effort: bool = False
    note: str | None = None


class AiFeatureSettingPatch(BaseModel):
    enabled: bool | None = None
    provider: ProviderName | None = None
    model: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    effort: str | None = Field(default=None, max_length=32)

    @field_validator("model", "effort")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PromptOut(BaseModel):
    key: str
    display_name: str
    default_template: str
    effective_template: str
    override_template: str | None = None
    has_override: bool
    variables: list[str]
    response_contract: str
    updated_at: datetime | None = None


class PromptPatch(BaseModel):
    template: str = Field(min_length=1)


class SecretPatch(BaseModel):
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    clear_openai_api_key: bool = False
    clear_anthropic_api_key: bool = False
    export_env: bool = True


class ProviderTestOut(BaseModel):
    provider: ProviderName
    ok: bool
    status: str
    error: str | None = None
    tested_at: datetime


class EnvExportStatus(BaseModel):
    available: bool
    path: str | None = None
    last_warning: str | None = None
    allowlisted_keys: list[str]


class BackgroundAiSettings(BaseModel):
    enabled: bool
    tasks: list[str]


class BackgroundAiPatch(BaseModel):
    enabled: bool
    tasks: list[str]

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, value: list[str]) -> list[str]:
        allowed = {"summarize", "extract_claims", "suggest_links"}
        deduped = []
        for task in value:
            if task not in allowed:
                raise ValueError(f"unsupported task: {task}")
            if task not in deduped:
                deduped.append(task)
        return deduped


class McpSettingsSummary(BaseModel):
    connection_count: int
    enabled_count: int
    web_search_threshold: float
    web_search_connection_name: str | None = None


class McpSettingsPatch(BaseModel):
    web_search_threshold: float = Field(ge=0, le=1)
    web_search_connection_name: str | None = None

    @field_validator("web_search_connection_name")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SettingsResponse(BaseModel):
    secrets: list[SecretStatus]
    features: list[AiFeatureSettingOut]
    prompts: list[PromptOut]
    background_ai: BackgroundAiSettings
    mcp: McpSettingsSummary
    env_export: EnvExportStatus
