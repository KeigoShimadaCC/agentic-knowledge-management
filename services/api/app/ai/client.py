from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent_run import AgentRun
from app.services.agent_run_service import create_agent_run, finish_agent_run

OPENAI_TEST_STUB_KEY = "sk-test-stub"
OPENAI_TEST_STUB_SUMMARY = "Canned E2E summary."


async def call_ai(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    agent_type: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
    input_context: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, AgentRun]:
    """Call the configured chat model and persist an agent_runs audit row."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="ai_disabled")

    selected_model = model or settings.openai_chat_model
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
        if settings.openai_api_key == OPENAI_TEST_STUB_KEY:
            text = OPENAI_TEST_STUB_SUMMARY
            await finish_agent_run(
                db,
                run,
                status="success",
                output={"text": text},
                input_tokens=10,
                output_tokens=8,
                cost_usd=Decimal("0"),
            )
            return text, run

        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        request_kwargs: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": settings.openai_max_tokens,
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        response = await client.chat.completions.create(**request_kwargs)
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        await finish_agent_run(
            db,
            run,
            status="success",
            output={"text": text},
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal("0"),
        )
        return text, run
    except Exception as exc:
        await finish_agent_run(db, run, status="error", error=str(exc))
        raise
