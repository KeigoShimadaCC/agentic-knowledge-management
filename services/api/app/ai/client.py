from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import (
    ANTHROPIC_TEST_STUB_KEY,
    OPENAI_TEST_STUB_KEY,
    TEST_STUB_SUMMARY,
    ChatProviderDisabledError,
    get_chat_provider,
)
from app.config import settings
from app.models.agent_run import AgentRun
from app.services.agent_run_service import create_agent_run, finish_agent_run

# Preserved exports for callers / tests that imported the legacy names.
OPENAI_TEST_STUB_SUMMARY = TEST_STUB_SUMMARY

__all__ = [
    "call_ai",
    "OPENAI_TEST_STUB_KEY",
    "ANTHROPIC_TEST_STUB_KEY",
    "OPENAI_TEST_STUB_SUMMARY",
    "TEST_STUB_SUMMARY",
]


async def call_ai(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    agent_type: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    provider: str | None = None,
    temperature: float = 0.2,
    input_context: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, AgentRun]:
    """Call the configured chat model and persist an agent_runs audit row.

    ``provider`` and ``model`` are optional per-call overrides; when omitted,
    we use ``settings.ai_provider`` and the provider's default chat model.
    """
    try:
        chat_provider = get_chat_provider(provider)
    except ChatProviderDisabledError as exc:
        raise HTTPException(status_code=503, detail="ai_disabled") from exc

    if not chat_provider.is_enabled:
        raise HTTPException(status_code=503, detail="ai_disabled")

    selected_model = model or chat_provider.default_model
    run_context = {"context": input_context or {}, "temperature": temperature}
    if response_format is not None:
        run_context["response_format"] = response_format

    run = await create_agent_run(
        db,
        user_id=user_id,
        agent_type=agent_type,
        input_payload=run_context,
        model=selected_model,
    )

    try:
        result = await chat_provider.complete(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            max_tokens=settings.openai_max_tokens,
            response_format=response_format,
        )
        await finish_agent_run(
            db,
            run,
            status="success",
            output={"text": result.text},
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=Decimal("0"),
        )
        return result.text, run
    except Exception as exc:
        await finish_agent_run(db, run, status="error", error=str(exc))
        raise
