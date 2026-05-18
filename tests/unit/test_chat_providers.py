"""Unit tests for the ChatProvider abstraction."""

from __future__ import annotations

import pytest

from app.ai.providers import (
    ANTHROPIC_JSON_INSTRUCTION,
    AnthropicChatProvider,
    ChatProviderDisabledError,
    OpenAIChatProvider,
    get_chat_provider,
    split_system_messages,
)


class TestSplitSystemMessages:
    def test_extracts_system_message_into_separate_arg(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        system, rest = split_system_messages(messages, json_mode=False)
        assert system == "You are helpful."
        assert rest == [{"role": "user", "content": "Hello"}]

    def test_concatenates_multiple_system_messages(self):
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "system", "content": "Use markdown."},
            {"role": "user", "content": "Hi"},
        ]
        system, rest = split_system_messages(messages, json_mode=False)
        assert system == "Be concise.\n\nUse markdown."
        assert len(rest) == 1

    def test_no_system_message_returns_none(self):
        messages = [{"role": "user", "content": "Hi"}]
        system, rest = split_system_messages(messages, json_mode=False)
        assert system is None
        assert rest == [{"role": "user", "content": "Hi"}]

    def test_json_mode_appends_instruction_when_system_present(self):
        messages = [
            {"role": "system", "content": "Return a project record."},
            {"role": "user", "content": "Extract this."},
        ]
        system, _ = split_system_messages(messages, json_mode=True)
        assert system is not None
        assert system.startswith("Return a project record.")
        assert system.endswith(ANTHROPIC_JSON_INSTRUCTION)

    def test_json_mode_creates_system_when_absent(self):
        messages = [{"role": "user", "content": "Give me JSON."}]
        system, _ = split_system_messages(messages, json_mode=True)
        assert system == ANTHROPIC_JSON_INSTRUCTION

    def test_user_role_defaults_when_role_missing(self):
        messages = [{"content": "no role"}]
        _, rest = split_system_messages(messages, json_mode=False)
        assert rest == [{"role": "user", "content": "no role"}]


class TestGetChatProvider:
    def test_default_provider_is_openai(self, monkeypatch):
        # ai_provider defaults to "openai" in Settings
        provider = get_chat_provider()
        assert isinstance(provider, OpenAIChatProvider)
        assert provider.name == "openai"

    def test_explicit_override_to_anthropic(self):
        provider = get_chat_provider("anthropic")
        assert isinstance(provider, AnthropicChatProvider)
        assert provider.name == "anthropic"

    def test_case_insensitive_selection(self):
        provider = get_chat_provider("ANTHROPIC")
        assert isinstance(provider, AnthropicChatProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ChatProviderDisabledError):
            get_chat_provider("ollama")


class TestProviderEnabled:
    def test_openai_enabled_when_key_set(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "openai_api_key", "sk-real")
        assert OpenAIChatProvider().is_enabled is True

    def test_openai_disabled_when_key_empty(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "openai_api_key", "")
        assert OpenAIChatProvider().is_enabled is False

    def test_anthropic_enabled_when_key_set(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-real")
        assert AnthropicChatProvider().is_enabled is True

    def test_anthropic_disabled_when_key_empty(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "anthropic_api_key", "")
        assert AnthropicChatProvider().is_enabled is False


@pytest.mark.asyncio
class TestAnthropicStub:
    async def test_stub_key_returns_canned_text(self, monkeypatch):
        from app.ai.providers import ANTHROPIC_TEST_STUB_KEY, TEST_STUB_SUMMARY
        from app.config import settings

        monkeypatch.setattr(settings, "anthropic_api_key", ANTHROPIC_TEST_STUB_KEY)
        result = await AnthropicChatProvider().complete(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-sonnet-4-6",
            temperature=0.2,
            max_tokens=100,
            response_format=None,
        )
        assert result.text == TEST_STUB_SUMMARY
        assert result.input_tokens == 10
        assert result.output_tokens == 8
