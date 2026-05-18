"""Integration test for AI provider switching.

Confirms that flipping ``settings.ai_provider`` to ``anthropic`` routes calls
through ``AnthropicChatProvider`` (no openai HTTP), and that the disabled-key
path returns 503.
"""

from __future__ import annotations

import pytest
from app.ai.providers import ANTHROPIC_TEST_STUB_KEY, TEST_STUB_SUMMARY
from app.config import settings
from httpx import AsyncClient


async def _make_page(auth_client: AsyncClient) -> dict:
    r = await auth_client.post("/api/v1/pages", json={"title": "Provider switch page"})
    assert r.status_code == 201, r.text
    data = r.json()
    page_id = data["page"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": "Provider abstraction lets us swap LLM backends."},
    )
    return data


@pytest.mark.asyncio
async def test_anthropic_stub_returns_canned_summary(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """With ai_provider=anthropic and stub key, summarize hits the canned path."""
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", ANTHROPIC_TEST_STUB_KEY)
    # No openai key needed; the dispatcher must not consult openai at all.
    monkeypatch.setattr(settings, "openai_api_key", "")

    page = await _make_page(auth_client)
    object_id = page["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Stub responses are now agent_type-aware (see app/ai/providers.stub_response_text)
    # — for "summarize" they include TEST_STUB_SUMMARY as a substring inside a longer
    # paragraph so SAI02-style "length > 50" e2e assertions also pass.
    assert TEST_STUB_SUMMARY in body["summary"]
    assert "agent_run_id" in body


@pytest.mark.asyncio
async def test_anthropic_without_key_returns_503(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """With ai_provider=anthropic but no anthropic key, summarize is disabled."""
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")

    page = await _make_page(auth_client)
    object_id = page["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "ai_disabled"


@pytest.mark.asyncio
async def test_unknown_provider_returns_503(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """ai_provider set to an unsupported value returns 503 ai_disabled (not 500)."""
    monkeypatch.setattr(settings, "ai_provider", "ollama")

    page = await _make_page(auth_client)
    object_id = page["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "ai_disabled"
