from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.settings import (
    AiFeatureSettingOut,
    AiFeatureSettingPatch,
    BackgroundAiPatch,
    BackgroundAiSettings,
    McpSettingsPatch,
    McpSettingsSummary,
    PromptOut,
    PromptPatch,
    ProviderTestOut,
    SecretPatch,
    SettingsResponse,
)
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
@router.get("/", response_model=SettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    return SettingsResponse(**await settings_service.settings_response(db, user_id=user.id))


@router.patch("/secrets", response_model=SettingsResponse)
async def patch_secrets(
    body: SecretPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    await settings_service.patch_secrets(
        db,
        user_id=user.id,
        openai_api_key=body.openai_api_key,
        anthropic_api_key=body.anthropic_api_key,
        clear_openai_api_key=body.clear_openai_api_key,
        clear_anthropic_api_key=body.clear_anthropic_api_key,
    )
    warning = await settings_service.export_env(db, user.id) if body.export_env else None
    await db.commit()
    return SettingsResponse(
        **await settings_service.settings_response(db, user_id=user.id, export_warning=warning)
    )


@router.post("/providers/{provider}/test", response_model=ProviderTestOut)
async def test_provider(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProviderTestOut:
    ok, error = await settings_service.test_provider(db, user_id=user.id, provider=provider)
    await db.commit()
    return ProviderTestOut(
        provider=provider,  # type: ignore[arg-type]
        ok=ok,
        status="success" if ok else "error",
        error=error,
        tested_at=datetime.now(UTC),
    )


@router.patch("/ai-features/{feature_key}", response_model=AiFeatureSettingOut)
async def patch_ai_feature(
    feature_key: str,
    body: AiFeatureSettingPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AiFeatureSettingOut:
    await settings_service.patch_ai_feature(
        db, user_id=user.id, feature_key=feature_key, patch=body
    )
    await db.commit()
    response = await settings_service.settings_response(db, user_id=user.id)
    return next(item for item in response["features"] if item.feature_key == feature_key)


@router.patch("/background-ai", response_model=BackgroundAiSettings)
async def patch_background_ai(
    body: BackgroundAiPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BackgroundAiSettings:
    result = await settings_service.patch_background_ai(db, user_id=user.id, patch=body)
    await db.commit()
    return result


@router.patch("/mcp", response_model=McpSettingsSummary)
async def patch_mcp_settings(
    body: McpSettingsPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> McpSettingsSummary:
    result = await settings_service.patch_mcp_settings(db, user_id=user.id, patch=body)
    await db.commit()
    return result


@router.patch("/prompts/{prompt_key}", response_model=PromptOut)
async def patch_prompt(
    prompt_key: str,
    body: PromptPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PromptOut:
    await settings_service.patch_prompt(
        db, user_id=user.id, prompt_key=prompt_key, template=body.template
    )
    await db.commit()
    response = await settings_service.settings_response(db, user_id=user.id)
    return next(item for item in response["prompts"] if item.key == prompt_key)


@router.post("/prompts/{prompt_key}/reset", response_model=PromptOut)
async def reset_prompt(
    prompt_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PromptOut:
    await settings_service.reset_prompt(db, user_id=user.id, prompt_key=prompt_key)
    await db.commit()
    response = await settings_service.settings_response(db, user_id=user.id)
    return next(item for item in response["prompts"] if item.key == prompt_key)


@router.post("/env/export", response_model=SettingsResponse)
async def export_env(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    warning = await settings_service.export_env(db, user.id)
    await db.commit()
    return SettingsResponse(
        **await settings_service.settings_response(db, user_id=user.id, export_warning=warning)
    )
