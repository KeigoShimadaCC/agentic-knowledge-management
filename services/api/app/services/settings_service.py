from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from string import Formatter
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ChatProviderDisabledError, get_chat_provider
from app.config import settings
from app.models.mcp_connection import McpConnection
from app.models.settings import (
    AiFeatureSetting,
    PromptOverride,
    SettingsPreference,
    SettingsProviderTest,
    SettingsSecret,
)
from app.schemas.settings import (
    AiFeatureSettingOut,
    AiFeatureSettingPatch,
    BackgroundAiPatch,
    BackgroundAiSettings,
    EnvExportStatus,
    McpSettingsPatch,
    McpSettingsSummary,
    PromptOut,
    SecretStatus,
)
from app.settings_registry import (
    AGENT_TYPE_TO_FEATURE,
    FEATURE_DEFINITIONS,
    PROMPT_DEFINITIONS,
    PROVIDER_CAPABILITIES,
)

SECRET_KEYS = ("openai_api_key", "anthropic_api_key")
SECRET_KEY_TO_PROVIDER = {"openai_api_key": "openai", "anthropic_api_key": "anthropic"}
PROVIDER_TO_SECRET_KEY = {v: k for k, v in SECRET_KEY_TO_PROVIDER.items()}

ENV_EXPORT_ALLOWLIST = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AI_PROVIDER",
    "OPENAI_CHAT_MODEL",
    "ANTHROPIC_CHAT_MODEL",
    "OPENAI_MAX_TOKENS",
    "ANTHROPIC_MAX_TOKENS",
    "AI_AUTO_PROCESS",
    "AI_AUTO_PROCESS_TASKS",
    "MCP_WEB_SEARCH_THRESHOLD",
    "MCP_WEB_SEARCH_CONNECTION_NAME",
]

PREF_BACKGROUND_AI = "background_ai"
PREF_MCP = "mcp"


@dataclass(frozen=True)
class ResolvedAiConfig:
    feature_key: str
    enabled: bool
    provider: str
    model: str
    temperature: float
    max_tokens: int
    api_key: str | None
    effort: str | None = None


def _fernet() -> Fernet:
    key = settings.settings_encryption_key or settings.mcp_env_encryption_key
    if not key:
        raise HTTPException(status_code=500, detail="settings_encryption_key_missing")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="settings_secret_decrypt_failed") from exc


def _redact(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return f"{value[:2]}..."
    return f"{value[:4]}...{value[-4:]}"


async def _secret_rows(db: AsyncSession, user_id: uuid.UUID) -> dict[str, SettingsSecret]:
    result = await db.execute(select(SettingsSecret).where(SettingsSecret.user_id == user_id))
    return {row.key: row for row in result.scalars().all()}


async def get_runtime_secret(db: AsyncSession, user_id: uuid.UUID, key: str) -> str | None:
    if key not in SECRET_KEYS:
        raise ValueError(f"unsupported secret key: {key}")
    rows = await _secret_rows(db, user_id)
    row = rows.get(key)
    return decrypt_secret(row.encrypted_value) if row else None


async def _set_secret(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    key: str,
    value: str | None,
    clear: bool,
) -> None:
    rows = await _secret_rows(db, user_id)
    row = rows.get(key)
    if clear or value == "":
        if row:
            await db.delete(row)
        return
    if value is None:
        return
    encrypted = encrypt_secret(value.strip())
    if row:
        row.encrypted_value = encrypted
        row.updated_at = datetime.now(UTC)
    else:
        db.add(SettingsSecret(user_id=user_id, key=key, encrypted_value=encrypted))


async def patch_secrets(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    openai_api_key: str | None,
    anthropic_api_key: str | None,
    clear_openai_api_key: bool,
    clear_anthropic_api_key: bool,
) -> None:
    await _set_secret(
        db,
        user_id=user_id,
        key="openai_api_key",
        value=openai_api_key,
        clear=clear_openai_api_key,
    )
    await _set_secret(
        db,
        user_id=user_id,
        key="anthropic_api_key",
        value=anthropic_api_key,
        clear=clear_anthropic_api_key,
    )
    await db.flush()


def _provider_default_model(provider: str) -> str:
    if provider == "anthropic":
        return settings.anthropic_chat_model
    return settings.openai_chat_model


def _provider_default_max_tokens(provider: str) -> int:
    if provider == "anthropic":
        return settings.anthropic_max_tokens
    return settings.openai_max_tokens


async def _feature_rows(db: AsyncSession, user_id: uuid.UUID) -> dict[str, AiFeatureSetting]:
    result = await db.execute(select(AiFeatureSetting).where(AiFeatureSetting.user_id == user_id))
    return {row.feature_key: row for row in result.scalars().all()}


async def _preference_rows(db: AsyncSession, user_id: uuid.UUID) -> dict[str, SettingsPreference]:
    result = await db.execute(
        select(SettingsPreference).where(SettingsPreference.user_id == user_id)
    )
    return {row.key: row for row in result.scalars().all()}


async def _provider_test_rows(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[str, SettingsProviderTest]:
    result = await db.execute(
        select(SettingsProviderTest).where(SettingsProviderTest.user_id == user_id)
    )
    return {row.provider: row for row in result.scalars().all()}


async def _set_preference(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    key: str,
    value: dict[str, Any],
) -> SettingsPreference:
    rows = await _preference_rows(db, user_id)
    row = rows.get(key)
    if row is None:
        row = SettingsPreference(user_id=user_id, key=key, value=value)
        db.add(row)
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def background_ai_settings(db: AsyncSession, user_id: uuid.UUID) -> BackgroundAiSettings:
    row = (await _preference_rows(db, user_id)).get(PREF_BACKGROUND_AI)
    value = row.value if row else {}
    return BackgroundAiSettings(
        enabled=bool(value.get("enabled", settings.ai_auto_process)),
        tasks=list(value.get("tasks") or settings.ai_auto_process_tasks),
    )


async def patch_background_ai(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    patch: BackgroundAiPatch,
) -> BackgroundAiSettings:
    value = {"enabled": patch.enabled, "tasks": patch.tasks}
    await _set_preference(db, user_id=user_id, key=PREF_BACKGROUND_AI, value=value)
    return BackgroundAiSettings(**value)


async def mcp_runtime_settings(db: AsyncSession, user_id: uuid.UUID) -> McpSettingsSummary:
    total = await db.scalar(
        select(func.count())
        .select_from(McpConnection)
        .where(
            McpConnection.user_id == user_id,
            McpConnection.deleted_at.is_(None),
        )
    )
    enabled = await db.scalar(
        select(func.count())
        .select_from(McpConnection)
        .where(
            McpConnection.user_id == user_id,
            McpConnection.enabled.is_(True),
            McpConnection.deleted_at.is_(None),
        )
    )
    row = (await _preference_rows(db, user_id)).get(PREF_MCP)
    value = row.value if row else {}
    return McpSettingsSummary(
        connection_count=total or 0,
        enabled_count=enabled or 0,
        web_search_threshold=float(
            value.get("web_search_threshold", settings.mcp_web_search_threshold)
        ),
        web_search_connection_name=(
            value.get("web_search_connection_name")
            or settings.mcp_web_search_connection_name
            or None
        ),
    )


async def patch_mcp_settings(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    patch: McpSettingsPatch,
) -> McpSettingsSummary:
    value = {
        "web_search_threshold": patch.web_search_threshold,
        "web_search_connection_name": patch.web_search_connection_name,
    }
    await _set_preference(db, user_id=user_id, key=PREF_MCP, value=value)
    return await mcp_runtime_settings(db, user_id)


async def resolve_ai_config(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    agent_type: str,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> ResolvedAiConfig:
    feature_key = AGENT_TYPE_TO_FEATURE.get(agent_type, agent_type)
    rows = await _feature_rows(db, user_id)
    row = rows.get(feature_key)
    enabled = True if row is None else row.enabled
    if not enabled:
        raise HTTPException(status_code=503, detail="ai_feature_disabled")

    selected_provider = (
        provider or (row.provider if row else None) or settings.ai_provider or "openai"
    ).lower()
    feature = FEATURE_DEFINITIONS.get(feature_key)
    selected_model = (
        model or (row.model if row else None) or (feature.default_model if feature else None)
    )
    selected_model = selected_model or _provider_default_model(selected_provider)
    selected_temperature = (
        temperature
        if temperature is not None
        else (row.temperature if row and row.temperature is not None else None)
    )
    if selected_temperature is None:
        selected_temperature = feature.default_temperature if feature else None
    if selected_temperature is None:
        selected_temperature = 0.2
    selected_max_tokens = (
        row.max_tokens
        if row and row.max_tokens is not None
        else _provider_default_max_tokens(selected_provider)
    )
    runtime_key = await get_runtime_secret(
        db, user_id, PROVIDER_TO_SECRET_KEY.get(selected_provider, "openai_api_key")
    )
    env_key = (
        settings.anthropic_api_key if selected_provider == "anthropic" else settings.openai_api_key
    )
    supports_effort = PROVIDER_CAPABILITIES.get(selected_provider, {}).get("effort", False)
    effort = row.effort if row and supports_effort else None
    return ResolvedAiConfig(
        feature_key=feature_key,
        enabled=enabled,
        provider=selected_provider,
        model=selected_model,
        temperature=selected_temperature,
        max_tokens=selected_max_tokens,
        api_key=runtime_key or env_key or None,
        effort=effort,
    )


async def patch_ai_feature(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    feature_key: str,
    patch: AiFeatureSettingPatch,
) -> AiFeatureSetting:
    if feature_key not in FEATURE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="feature_not_found")
    rows = await _feature_rows(db, user_id)
    row = rows.get(feature_key)
    if row is None:
        row = AiFeatureSetting(user_id=user_id, feature_key=feature_key)
        db.add(row)
        await db.flush()
    data = patch.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def prompt_template(db: AsyncSession, user_id: uuid.UUID, prompt_key: str) -> str:
    definition = PROMPT_DEFINITIONS.get(prompt_key)
    if definition is None:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    result = await db.execute(
        select(PromptOverride).where(
            PromptOverride.user_id == user_id,
            PromptOverride.prompt_key == prompt_key,
        )
    )
    row = result.scalar_one_or_none()
    return row.template if row else definition.default_template


async def render_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
    prompt_key: str,
    **variables: Any,
) -> str:
    template = await prompt_template(db, user_id, prompt_key)
    try:
        return template.format(**variables)
    except KeyError as exc:
        raise HTTPException(
            status_code=422, detail=f"missing_prompt_variable:{exc.args[0]}"
        ) from exc


def _template_variables(template: str) -> set[str]:
    return {
        field_name.split(".")[0].split("[")[0]
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }


def validate_prompt_template(prompt_key: str, template: str) -> None:
    definition = PROMPT_DEFINITIONS.get(prompt_key)
    if definition is None:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    found = _template_variables(template)
    expected = set(definition.variables)
    missing = expected - found
    unknown = found - expected
    if missing or unknown:
        raise HTTPException(
            status_code=422,
            detail={"missing_variables": sorted(missing), "unknown_variables": sorted(unknown)},
        )


async def patch_prompt(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    prompt_key: str,
    template: str,
) -> PromptOverride:
    validate_prompt_template(prompt_key, template)
    result = await db.execute(
        select(PromptOverride).where(
            PromptOverride.user_id == user_id,
            PromptOverride.prompt_key == prompt_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = PromptOverride(user_id=user_id, prompt_key=prompt_key, template=template)
        db.add(row)
    else:
        row.template = template
        row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def reset_prompt(db: AsyncSession, *, user_id: uuid.UUID, prompt_key: str) -> None:
    if prompt_key not in PROMPT_DEFINITIONS:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    result = await db.execute(
        select(PromptOverride).where(
            PromptOverride.user_id == user_id,
            PromptOverride.prompt_key == prompt_key,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.flush()


def _env_export_path() -> Path | None:
    if not settings.settings_env_file_path:
        return None
    return Path(settings.settings_env_file_path)


def _serialize_env_value(value: str | int | float | bool | list[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(value)
    return str(value)


def _replace_or_append_env(content: str, values: dict[str, str]) -> str:
    lines = content.splitlines()
    seen: set[str] = set()
    rendered: list[str] = []
    key_re = re.compile(r"^([A-Z0-9_]+)=")
    for line in lines:
        match = key_re.match(line)
        if match and match.group(1) in values:
            key = match.group(1)
            rendered.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            rendered.append(line)
    for key in ENV_EXPORT_ALLOWLIST:
        if key in values and key not in seen:
            rendered.append(f"{key}={values[key]}")
    return "\n".join(rendered) + ("\n" if content.endswith("\n") or rendered else "")


async def export_env(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    path = _env_export_path()
    if path is None:
        return "SETTINGS_ENV_FILE_PATH is not configured"
    try:
        rows = await _secret_rows(db, user_id)
        background = await background_ai_settings(db, user_id)
        mcp = await mcp_runtime_settings(db, user_id)
        openai_key = (
            decrypt_secret(rows["openai_api_key"].encrypted_value)
            if "openai_api_key" in rows
            else settings.openai_api_key
        )
        anthropic_key = (
            decrypt_secret(rows["anthropic_api_key"].encrypted_value)
            if "anthropic_api_key" in rows
            else settings.anthropic_api_key
        )
        values = {
            "OPENAI_API_KEY": openai_key,
            "ANTHROPIC_API_KEY": anthropic_key,
            "AI_PROVIDER": settings.ai_provider,
            "OPENAI_CHAT_MODEL": settings.openai_chat_model,
            "ANTHROPIC_CHAT_MODEL": settings.anthropic_chat_model,
            "OPENAI_MAX_TOKENS": _serialize_env_value(settings.openai_max_tokens),
            "ANTHROPIC_MAX_TOKENS": _serialize_env_value(settings.anthropic_max_tokens),
            "AI_AUTO_PROCESS": _serialize_env_value(background.enabled),
            "AI_AUTO_PROCESS_TASKS": _serialize_env_value(background.tasks),
            "MCP_WEB_SEARCH_THRESHOLD": _serialize_env_value(mcp.web_search_threshold),
            "MCP_WEB_SEARCH_CONNECTION_NAME": mcp.web_search_connection_name or "",
        }
        content = path.read_text() if path.exists() else ""
        path.write_text(_replace_or_append_env(content, values))
    except OSError as exc:
        return str(exc)
    return None


async def settings_response(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    export_warning: str | None = None,
) -> dict[str, Any]:
    secrets = await _secret_rows(db, user_id)
    tests = await _provider_test_rows(db, user_id)
    secret_out: list[SecretStatus] = []
    for key in SECRET_KEYS:
        row = secrets.get(key)
        provider = SECRET_KEY_TO_PROVIDER[key]
        test_row = tests.get(provider)
        env_value = getattr(settings, key)
        raw = decrypt_secret(row.encrypted_value) if row else env_value
        source = "runtime" if row else ("env" if env_value else "none")
        secret_out.append(
            SecretStatus(
                key=key,
                configured=bool(raw),
                source=source,
                redacted=_redact(raw),
                last_test_status=test_row.status if test_row else None,
                last_test_error=test_row.error if test_row else None,
                last_tested_at=test_row.tested_at if test_row else None,
            )
        )

    feature_rows = await _feature_rows(db, user_id)
    feature_out: list[AiFeatureSettingOut] = []
    for key, definition in FEATURE_DEFINITIONS.items():
        row = feature_rows.get(key)
        provider = (
            row.provider
            if row and row.provider
            else definition.default_provider or settings.ai_provider
        )
        provider = provider.lower() if provider else None
        model = row.model if row and row.model else definition.default_model
        if key == "embeddings_search":
            model = model or settings.embedding_model
        elif provider:
            model = model or _provider_default_model(provider)
        temperature = (
            row.temperature
            if row and row.temperature is not None
            else definition.default_temperature
        )
        max_tokens = row.max_tokens if row and row.max_tokens is not None else None
        if max_tokens is None and provider:
            max_tokens = _provider_default_max_tokens(provider)
        supports_effort = bool(provider and PROVIDER_CAPABILITIES.get(provider, {}).get("effort"))
        note = None
        effort = row.effort if row else None
        if effort and not supports_effort:
            note = "Effort is stored but ignored by the selected provider."
        feature_out.append(
            AiFeatureSettingOut(
                feature_key=key,
                display_name=definition.display_name,
                enabled=True if row is None else row.enabled,
                provider=row.provider if row else None,
                model=row.model if row else None,
                temperature=row.temperature if row else None,
                max_tokens=row.max_tokens if row else None,
                effort=effort,
                resolved_provider=provider,
                resolved_model=model,
                resolved_temperature=temperature,
                resolved_max_tokens=max_tokens,
                supports_effort=supports_effort,
                note=note,
            )
        )

    result = await db.execute(select(PromptOverride).where(PromptOverride.user_id == user_id))
    overrides = {row.prompt_key: row for row in result.scalars().all()}
    prompt_out = [
        PromptOut(
            key=definition.key,
            display_name=definition.display_name,
            default_template=definition.default_template,
            effective_template=overrides[definition.key].template
            if definition.key in overrides
            else definition.default_template,
            override_template=overrides[definition.key].template
            if definition.key in overrides
            else None,
            has_override=definition.key in overrides,
            variables=list(definition.variables),
            response_contract=definition.response_contract,
            updated_at=overrides[definition.key].updated_at
            if definition.key in overrides
            else None,
        )
        for definition in PROMPT_DEFINITIONS.values()
    ]

    path = _env_export_path()
    return {
        "secrets": secret_out,
        "features": feature_out,
        "prompts": prompt_out,
        "background_ai": await background_ai_settings(db, user_id),
        "mcp": await mcp_runtime_settings(db, user_id),
        "env_export": EnvExportStatus(
            available=bool(path),
            path=str(path) if path else None,
            last_warning=export_warning,
            allowlisted_keys=ENV_EXPORT_ALLOWLIST,
        ),
    }


async def test_provider(
    db: AsyncSession, *, user_id: uuid.UUID, provider: str
) -> tuple[bool, str | None]:
    if provider not in PROVIDER_TO_SECRET_KEY:
        raise HTTPException(status_code=404, detail="provider_not_found")
    key = await get_runtime_secret(db, user_id, PROVIDER_TO_SECRET_KEY[provider])
    key = key or (
        settings.anthropic_api_key if provider == "anthropic" else settings.openai_api_key
    )
    row_map = await _secret_rows(db, user_id)
    secret_row = row_map.get(PROVIDER_TO_SECRET_KEY[provider])
    tested_at = datetime.now(UTC)

    async def record(status: str, error: str | None) -> None:
        rows = await _provider_test_rows(db, user_id)
        row = rows.get(provider)
        if row is None:
            db.add(
                SettingsProviderTest(
                    user_id=user_id,
                    provider=provider,
                    status=status,
                    error=error,
                    tested_at=tested_at,
                )
            )
        else:
            row.status = status
            row.error = error
            row.tested_at = tested_at
            row.updated_at = tested_at
        if secret_row:
            secret_row.last_test_status = status
            secret_row.last_test_error = error
            secret_row.last_tested_at = tested_at
        await db.flush()

    try:
        chat_provider = get_chat_provider(provider)
    except ChatProviderDisabledError as exc:
        error = str(exc)
        await record("error", error)
        return False, error
    try:
        if not key:
            raise RuntimeError("provider key is not configured")
        await chat_provider.complete(
            messages=[{"role": "user", "content": "Reply with ok."}],
            model=chat_provider.default_model,
            temperature=0,
            max_tokens=16,
            response_format=None,
            api_key=key,
        )
        await record("success", None)
        return True, None
    except Exception as exc:
        error = str(exc)
        await record("error", error)
        return False, error
