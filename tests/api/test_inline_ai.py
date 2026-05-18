"""Integration tests for Phase 11B inline AI endpoints (/ai/complete, /ai/transform).

OpenAI calls are patched — no real API calls are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _make_openai_mock(content: str = "AI generated text.") -> MagicMock:
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=content))]
    mock_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    client_mock = MagicMock()
    client_mock.chat = MagicMock()
    client_mock.chat.completions = MagicMock()
    client_mock.chat.completions.create = AsyncMock(return_value=mock_completion)
    return client_mock


@pytest.fixture
def mock_openai():
    """Patch openai.AsyncOpenAI so no real HTTP calls happen."""
    client_mock = _make_openai_mock()
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        yield client_mock


# ── /ai/complete ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_continue(auth_client: AsyncClient, mock_openai: MagicMock):
    resp = await auth_client.post(
        "/api/v1/ai/complete",
        json={
            "context_before": "The main limitation of this approach is",
            "instruction": "continue",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completion"] == "AI generated text."
    assert "agent_run_id" in data


@pytest.mark.asyncio
async def test_complete_expand(auth_client: AsyncClient, mock_openai: MagicMock):
    resp = await auth_client.post(
        "/api/v1/ai/complete",
        json={"context_before": "Machine learning is a subset of AI.", "instruction": "expand"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "completion" in data
    assert "agent_run_id" in data


@pytest.mark.asyncio
async def test_complete_empty_context_before(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/ai/complete",
        json={"context_before": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_complete_max_tokens_over_limit(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/ai/complete",
        json={"context_before": "Some text.", "max_tokens": 600},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_complete_no_api_key(auth_client: AsyncClient):
    from app.ai import providers as providers_module

    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post(
            "/api/v1/ai/complete",
            json={"context_before": "Some text to complete."},
        )
    assert resp.status_code == 503


# ── /ai/transform ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("instruction", ["improve", "concise", "grammar", "summarize"])
async def test_transform_all_instructions(
    auth_client: AsyncClient, mock_openai: MagicMock, instruction: str
):
    resp = await auth_client.post(
        "/api/v1/ai/transform",
        json={"text": "This is some text to transform.", "instruction": instruction},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "AI generated text."
    assert "agent_run_id" in data


@pytest.mark.asyncio
async def test_transform_empty_text(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/v1/ai/transform",
        json={"text": "", "instruction": "improve"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transform_no_api_key(auth_client: AsyncClient):
    from app.ai import providers as providers_module

    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post(
            "/api/v1/ai/transform",
            json={"text": "Some text.", "instruction": "improve"},
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_transform_empty_llm_response(auth_client: AsyncClient):
    """LLM returning empty string should produce 200 with result=''."""
    client_mock = _make_openai_mock(content="")
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/transform",
            json={"text": "Some text.", "instruction": "improve"},
        )
    assert resp.status_code == 200
    assert resp.json()["result"] == ""
