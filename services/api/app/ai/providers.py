"""Chat provider abstraction.

Pattern mirrors ``app.search.embedding`` (ABC + concrete impls + factory) so
chat and embeddings stay decoupled and future providers (Ollama, local
runtimes) plug in without touching call sites.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass
from typing import Any

from app.config import settings

TEST_STUB_SUMMARY = "Canned E2E summary."
OPENAI_TEST_STUB_KEY = "sk-test-stub"
ANTHROPIC_TEST_STUB_KEY = "sk-ant-test-stub"

ANTHROPIC_JSON_INSTRUCTION = (
    "You MUST respond with a single valid JSON object only. "
    "Do not include prose, markdown, or code fences."
)

# Long-form stub keeps "Canned E2E summary." as a substring so existing UI text
# assertions still pass, while staying well over 50 chars for SAI02-style
# "length > 50" assertions in tests/e2e/specs/30-sai02-page-intelligence.spec.ts.
_STUB_LONG_SUMMARY = (
    f"{TEST_STUB_SUMMARY} This deterministic stub paragraph stays well over fifty "
    "characters so end-to-end summarize and answer tests can assert on length "
    "without ever calling a real model."
)

# JSON stubs keyed by agent_type. Shapes follow the schemas the corresponding
# services parse (see career_ai_service and ai_service).
_STUB_BULLETS_JSON = json.dumps(
    {
        "bullets": [
            {
                "text": (
                    f"{TEST_STUB_SUMMARY} Stub bullet 1 covering a measurable "
                    "outcome for e2e bullet-count assertions."
                ),
                "evidence_object_ids": [],
                "confidence": "medium",
                "metrics_cited": ["stub_metric"],
            },
            {
                "text": "Stub bullet 2 documenting a deterministic e2e scenario.",
                "evidence_object_ids": [],
                "confidence": "medium",
                "metrics_cited": [],
            },
            {
                "text": "Stub bullet 3 — the SAI01 spec requires at least three.",
                "evidence_object_ids": [],
                "confidence": "low",
                "metrics_cited": [],
            },
        ]
    }
)

_STUB_INTERVIEW_STORY_JSON = json.dumps(
    {
        "situation": "Stub e2e situation describing the project setup.",
        "task": "Stub e2e task describing what needed to be done.",
        "action": "Stub e2e action describing the deterministic steps taken.",
        "result": "Stub e2e result quantifying the deterministic outcome.",
        "evidence_object_ids": [],
    }
)

_STUB_TRIAGE_JSON = json.dumps(
    {
        "summary": (
            f"{TEST_STUB_SUMMARY} Stub triage summary exceeding the 30-char "
            "threshold SAI03 asserts on."
        ),
        "suggested_tags": ["stub", "e2e"],
        "suggested_title": "Stub triage title",
    }
)

_STUB_EXTRACT_PROJECT_JSON = json.dumps(
    {
        "title": "Stub e2e project",
        "summary": f"{TEST_STUB_SUMMARY} Stub project summary for extract-project flows.",
        "role": "",
        "outcomes": [],
        "tags": ["stub"],
    }
)


def stub_response_text(agent_type: str | None) -> str:
    """Return shape-appropriate stub text for the given agent_type.

    Used by both provider stubs (OpenAI + Anthropic) when their respective test
    keys are configured. Default falls back to the original short stub so the
    legacy "stub key returns canned text" unit test in
    tests/unit/test_chat_providers.py keeps passing.
    """
    if agent_type in ("summarize", "answer", "inline_ai_complete", "inline_ai_transform"):
        return _STUB_LONG_SUMMARY
    if agent_type == "generate_resume_bullets":
        return _STUB_BULLETS_JSON
    if agent_type == "generate_interview_story":
        return _STUB_INTERVIEW_STORY_JSON
    if agent_type == "triage":
        return _STUB_TRIAGE_JSON
    if agent_type == "extract-project":
        return _STUB_EXTRACT_PROJECT_JSON
    if agent_type in ("extract_claims", "extract_tasks", "suggest_links"):
        return "[]"
    return TEST_STUB_SUMMARY


@dataclass
class ChatResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None


class ChatProviderDisabledError(Exception):
    """Raised when the active chat provider has no API key configured."""


class ChatProvider(abc.ABC):
    name: str

    @property
    @abc.abstractmethod
    def default_model(self) -> str: ...

    @property
    @abc.abstractmethod
    def is_enabled(self) -> bool: ...

    @abc.abstractmethod
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
        agent_type: str | None = None,
    ) -> ChatResult: ...


class OpenAIChatProvider(ChatProvider):
    name = "openai"

    @property
    def default_model(self) -> str:
        return settings.openai_chat_model

    @property
    def is_enabled(self) -> bool:
        return bool(settings.openai_api_key)

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
        agent_type: str | None = None,
    ) -> ChatResult:
        if settings.openai_api_key == OPENAI_TEST_STUB_KEY:
            return ChatResult(
                text=stub_response_text(agent_type), input_tokens=10, output_tokens=8
            )

        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        response = await client.chat.completions.create(**request_kwargs)
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        return ChatResult(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )


def split_system_messages(
    messages: list[dict[str, str]],
    *,
    json_mode: bool,
) -> tuple[str | None, list[dict[str, str]]]:
    """Convert OpenAI-style messages (system role inline) to Anthropic shape.

    Anthropic takes ``system`` as a separate kwarg and rejects role='system' in
    the messages array. We concatenate any system messages (in order) into a
    single system string; when ``json_mode`` is set we append the JSON-only
    instruction so Anthropic emulates OpenAI's ``response_format``.
    """
    system_parts: list[str] = []
    other: list[dict[str, str]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            if content:
                system_parts.append(content)
        else:
            other.append({"role": role or "user", "content": content})

    if json_mode:
        system_parts.append(ANTHROPIC_JSON_INSTRUCTION)

    system = "\n\n".join(system_parts) if system_parts else None
    return system, other


class AnthropicChatProvider(ChatProvider):
    name = "anthropic"

    @property
    def default_model(self) -> str:
        return settings.anthropic_chat_model

    @property
    def is_enabled(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
        agent_type: str | None = None,
    ) -> ChatResult:
        json_mode = bool(response_format and response_format.get("type") == "json_object")
        system, anth_messages = split_system_messages(messages, json_mode=json_mode)

        if settings.anthropic_api_key == ANTHROPIC_TEST_STUB_KEY:
            return ChatResult(
                text=stub_response_text(agent_type), input_tokens=10, output_tokens=8
            )

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": anth_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system is not None:
            request_kwargs["system"] = system

        response = await client.messages.create(**request_kwargs)
        text_parts = [
            getattr(block, "text", "")
            for block in (response.content or [])
            if getattr(block, "type", None) == "text"
        ]
        text = "".join(text_parts)
        usage = getattr(response, "usage", None)
        return ChatResult(
            text=text,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )


_PROVIDERS: dict[str, type[ChatProvider]] = {
    "openai": OpenAIChatProvider,
    "anthropic": AnthropicChatProvider,
}


def get_chat_provider(name: str | None = None) -> ChatProvider:
    selected = (name or settings.ai_provider or "openai").lower()
    cls = _PROVIDERS.get(selected)
    if cls is None:
        raise ChatProviderDisabledError(
            f"Unknown ai_provider '{selected}'. Supported: {sorted(_PROVIDERS)}."
        )
    return cls()
