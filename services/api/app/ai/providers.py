"""Chat provider abstraction.

Pattern mirrors ``app.search.embedding`` (ABC + concrete impls + factory) so
chat and embeddings stay decoupled and future providers (Ollama, local
runtimes) plug in without touching call sites.
"""

from __future__ import annotations

import abc
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
    ) -> ChatResult:
        if settings.openai_api_key == OPENAI_TEST_STUB_KEY:
            return ChatResult(text=TEST_STUB_SUMMARY, input_tokens=10, output_tokens=8)

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
    ) -> ChatResult:
        json_mode = bool(response_format and response_format.get("type") == "json_object")
        system, anth_messages = split_system_messages(messages, json_mode=json_mode)

        if settings.anthropic_api_key == ANTHROPIC_TEST_STUB_KEY:
            return ChatResult(text=TEST_STUB_SUMMARY, input_tokens=10, output_tokens=8)

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
