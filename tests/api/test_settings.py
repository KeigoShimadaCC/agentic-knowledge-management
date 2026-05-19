from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.providers import ANTHROPIC_TEST_STUB_KEY, OPENAI_TEST_STUB_KEY, TEST_STUB_SUMMARY
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.settings import SettingsSecret
from app.models.user import User
from app.schemas.search import SearchResult
from app.services.settings_service import ENV_EXPORT_ALLOWLIST, render_prompt
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_settings_get_returns_redacted_status(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/settings")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {item["key"] for item in body["secrets"]} == {
        "openai_api_key",
        "anthropic_api_key",
    }
    assert body["prompts"]
    assert any(prompt["key"] == "summarize.page" for prompt in body["prompts"])
    assert any(feature["feature_key"] == "summarize" for feature in body["features"])
    assert "background_ai" in body
    assert body["mcp"]["connection_count"] == 0


@pytest.mark.asyncio
async def test_secret_save_is_redacted_and_runtime_provider_is_used(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")

    resp = await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"anthropic_api_key": ANTHROPIC_TEST_STUB_KEY, "export_env": False},
    )
    assert resp.status_code == 200, resp.text
    secret = next(item for item in resp.json()["secrets"] if item["key"] == "anthropic_api_key")
    assert secret["configured"] is True
    assert secret["source"] == "runtime"
    assert secret["redacted"] != ANTHROPIC_TEST_STUB_KEY

    page = await auth_client.post("/api/v1/pages", json={"title": "Runtime key page"})
    page_id = page.json()["page"]["id"]
    object_id = page.json()["object"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": "Runtime settings should enable Anthropic."},
    )
    ai_resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert ai_resp.status_code == 200, ai_resp.text
    assert TEST_STUB_SUMMARY in ai_resp.json()["summary"]


@pytest.mark.asyncio
async def test_provider_test_records_status_for_env_key(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", ANTHROPIC_TEST_STUB_KEY)

    resp = await auth_client.post("/api/v1/settings/providers/anthropic/test")
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    settings_resp = await auth_client.get("/api/v1/settings")
    secret = next(
        item for item in settings_resp.json()["secrets"] if item["key"] == "anthropic_api_key"
    )
    assert secret["source"] == "env"
    assert secret["last_test_status"] == "success"


@pytest.mark.asyncio
async def test_prompt_override_validation_save_and_reset(auth_client: AsyncClient):
    bad = await auth_client.patch(
        "/api/v1/settings/prompts/summarize.page",
        json={"template": "No variable here"},
    )
    assert bad.status_code == 422

    custom = "Custom summary prompt: {content}"
    saved = await auth_client.patch(
        "/api/v1/settings/prompts/summarize.page",
        json={"template": custom},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["has_override"] is True
    assert saved.json()["effective_template"] == custom

    reset = await auth_client.post("/api/v1/settings/prompts/summarize.page/reset")
    assert reset.status_code == 200, reset.text
    assert reset.json()["has_override"] is False


@pytest.mark.asyncio
async def test_ai_feature_config_controls_provider_and_model(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"anthropic_api_key": ANTHROPIC_TEST_STUB_KEY, "export_env": False},
    )
    resp = await auth_client.patch(
        "/api/v1/settings/ai-features/summarize",
        json={"provider": "anthropic", "model": "claude-test-model", "temperature": 0.4},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resolved_provider"] == "anthropic"
    assert resp.json()["resolved_model"] == "claude-test-model"

    page = await auth_client.post("/api/v1/pages", json={"title": "Feature config page"})
    page_id = page.json()["page"]["id"]
    object_id = page.json()["object"]["id"]
    await auth_client.patch(f"/api/v1/pages/{page_id}", json={"content_text": "Use config."})
    ai_resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert ai_resp.status_code == 200, ai_resp.text
    assert TEST_STUB_SUMMARY in ai_resp.json()["summary"]


@pytest.mark.asyncio
async def test_settings_secrets_encrypted_at_rest(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "openai_api_key", "")
    plaintext = "sk-secret-plaintext-for-encryption-test"

    resp = await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"openai_api_key": plaintext, "export_env": False},
    )
    assert resp.status_code == 200, resp.text

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SettingsSecret).where(SettingsSecret.key == "openai_api_key")
        )
        row = result.scalar_one()

    assert row.encrypted_value != plaintext


@pytest.mark.asyncio
async def test_clear_runtime_secret(auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    saved = await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"openai_api_key": OPENAI_TEST_STUB_KEY, "export_env": False},
    )
    assert saved.status_code == 200, saved.text

    cleared = await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"clear_openai_api_key": True, "export_env": False},
    )
    assert cleared.status_code == 200, cleared.text

    secret = next(item for item in cleared.json()["secrets"] if item["key"] == "openai_api_key")
    assert secret["configured"] is False
    assert secret["source"] == "none"


@pytest.mark.asyncio
async def test_env_export_writes_allowlisted_keys(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path
):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=1\n")
    monkeypatch.setattr(settings, "settings_env_file_path", str(env_file))
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    resp = await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"openai_api_key": OPENAI_TEST_STUB_KEY, "export_env": True},
    )
    assert resp.status_code == 200, resp.text
    assert OPENAI_TEST_STUB_KEY not in resp.text

    content = env_file.read_text()
    for key in ENV_EXPORT_ALLOWLIST:
        assert f"{key}=" in content
    assert f"OPENAI_API_KEY={OPENAI_TEST_STUB_KEY}" in content

    export_resp = await auth_client.post("/api/v1/settings/env/export")
    assert export_resp.status_code == 200, export_resp.text
    assert export_resp.json()["env_export"]["available"] is True


@pytest.mark.asyncio
async def test_ai_feature_disabled_blocks_summarize(auth_client: AsyncClient):
    disabled = await auth_client.patch(
        "/api/v1/settings/ai-features/summarize",
        json={"enabled": False},
    )
    assert disabled.status_code == 200, disabled.text

    page = await auth_client.post("/api/v1/pages", json={"title": "Disabled feature page"})
    page_id = page.json()["page"]["id"]
    object_id = page.json()["object"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": "Should not summarize."},
    )

    ai_resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert ai_resp.status_code == 503, ai_resp.text
    assert ai_resp.json()["detail"] == "ai_feature_disabled"


@pytest.mark.asyncio
async def test_prompt_override_is_used_for_summarize(auth_client: AsyncClient):
    custom = "Custom summary prompt: {content}"
    saved = await auth_client.patch(
        "/api/v1/settings/prompts/summarize.page",
        json={"template": custom},
    )
    assert saved.status_code == 200, saved.text

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User))).scalar_one()
        rendered = await render_prompt(db, user.id, "summarize.page", content="hello world")

    assert rendered == "Custom summary prompt: hello world"


@pytest.fixture
def mock_openai():
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=TEST_STUB_SUMMARY))]
    mock_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

    client_mock = MagicMock()
    client_mock.chat = MagicMock()
    client_mock.chat.completions = MagicMock()
    client_mock.chat.completions.create = AsyncMock(return_value=mock_completion)
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        yield client_mock


@pytest.mark.asyncio
async def test_summarize_endpoint_sends_rendered_prompt_override_to_model(
    auth_client: AsyncClient, mock_openai: MagicMock
):
    custom = "Custom summary prompt for E2E: {content}"
    saved = await auth_client.patch(
        "/api/v1/settings/prompts/summarize.page",
        json={"template": custom},
    )
    assert saved.status_code == 200, saved.text

    page = await auth_client.post("/api/v1/pages", json={"title": "Prompt override E2E"})
    page_id = page.json()["page"]["id"]
    object_id = page.json()["object"]["id"]
    page_text = "Python was created by Guido van Rossum in 1991."
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": page_text},
    )

    ai_resp = await auth_client.post(
        "/api/v1/ai/summarize",
        json={"object_id": object_id, "force": True},
    )
    assert ai_resp.status_code == 200, ai_resp.text

    mock_openai.chat.completions.create.assert_awaited()
    call = mock_openai.chat.completions.create.await_args
    assert call is not None
    messages = call.kwargs["messages"]
    assert "Custom summary prompt for E2E:" in messages[0]["content"]
    assert page_text in messages[0]["content"]

    reset = await auth_client.post("/api/v1/settings/prompts/summarize.page/reset")
    assert reset.status_code == 200, reset.text


@pytest.mark.asyncio
async def test_answer_endpoint_sends_rendered_prompt_override_to_model(
    auth_client: AsyncClient, mock_openai: MagicMock
):
    custom = "E2E answer: {question}\n{context}"
    saved = await auth_client.patch(
        "/api/v1/settings/prompts/answer.kb",
        json={"template": custom},
    )
    assert saved.status_code == 200, saved.text

    question = "What is quantum entanglement?"
    ai_resp = await auth_client.post("/api/v1/ai/answer", json={"q": question})
    assert ai_resp.status_code == 200, ai_resp.text

    mock_openai.chat.completions.create.assert_awaited()
    call = mock_openai.chat.completions.create.await_args
    assert call is not None
    messages = call.kwargs["messages"]
    assert "E2E answer:" in messages[0]["content"]
    assert question in messages[0]["content"]

    reset = await auth_client.post("/api/v1/settings/prompts/answer.kb/reset")
    assert reset.status_code == 200, reset.text


@pytest.mark.asyncio
async def test_suggest_links_endpoint_sends_rendered_prompt_override_to_model(
    auth_client: AsyncClient, mock_openai: MagicMock
):
    custom = "E2E suggest links: {title} | {content} | {candidates} | limit={limit}"
    saved = await auth_client.patch(
        "/api/v1/settings/prompts/suggest.links",
        json={"template": custom},
    )
    assert saved.status_code == 200, saved.text

    source = await auth_client.post(
        "/api/v1/pages",
        json={"title": "Quantum Entanglement Notes"},
    )
    assert source.status_code == 201, source.text
    source_page_id = source.json()["page"]["id"]
    source_object_id = source.json()["object"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{source_page_id}",
        json={
            "content_text": "Quantum entanglement is a physical phenomenon in quantum mechanics."
        },
    )

    related = await auth_client.post(
        "/api/v1/pages",
        json={"title": "Quantum Computing Overview"},
    )
    assert related.status_code == 201, related.text
    related_object_id = related.json()["object"]["id"]

    mock_openai.chat.completions.create.return_value.choices[0].message.content = "[]"

    fake_candidate = SearchResult(
        id=uuid.UUID(related_object_id),
        kind="page",
        title="Quantum Computing Overview",
        snippet=None,
        score=0.9,
        updated_at=datetime.now(UTC),
    )

    with patch(
        "app.services.ai_service.keyword_search",
        new_callable=AsyncMock,
        return_value=[fake_candidate],
    ):
        ai_resp = await auth_client.post(
            "/api/v1/ai/suggest-links",
            json={"object_id": source_object_id},
        )
    assert ai_resp.status_code == 200, ai_resp.text

    mock_openai.chat.completions.create.assert_awaited()
    call = mock_openai.chat.completions.create.await_args
    assert call is not None
    messages = call.kwargs["messages"]
    assert "E2E suggest links:" in messages[0]["content"]
    assert "Quantum Entanglement Notes" in messages[0]["content"]
    assert "limit=" in messages[0]["content"]

    reset = await auth_client.post("/api/v1/settings/prompts/suggest.links/reset")
    assert reset.status_code == 200, reset.text


@pytest.fixture
def mock_anthropic():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text=TEST_STUB_SUMMARY)]

    client_mock = MagicMock()
    client_mock.messages = MagicMock()
    client_mock.messages.create = AsyncMock(return_value=mock_message)
    with patch("anthropic.AsyncAnthropic", return_value=client_mock):
        yield client_mock


@pytest.mark.asyncio
async def test_summarize_uses_per_feature_model_in_provider_call(
    auth_client: AsyncClient, mock_anthropic: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    integration_key = "sk-ant-integration-test-key"
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    await auth_client.patch(
        "/api/v1/settings/secrets",
        json={"anthropic_api_key": integration_key, "export_env": False},
    )
    feature_resp = await auth_client.patch(
        "/api/v1/settings/ai-features/summarize",
        json={"provider": "anthropic", "model": "claude-test-model", "temperature": 0.4},
    )
    assert feature_resp.status_code == 200, feature_resp.text

    page = await auth_client.post("/api/v1/pages", json={"title": "Feature model E2E"})
    page_id = page.json()["page"]["id"]
    object_id = page.json()["object"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": "Per-feature model should reach Anthropic client."},
    )

    ai_resp = await auth_client.post(
        "/api/v1/ai/summarize",
        json={"object_id": object_id, "force": True},
    )
    assert ai_resp.status_code == 200, ai_resp.text

    mock_anthropic.messages.create.assert_awaited()
    call = mock_anthropic.messages.create.await_args
    assert call is not None
    assert call.kwargs["model"] == "claude-test-model"


@pytest.mark.asyncio
async def test_background_and_mcp_settings_patch(auth_client: AsyncClient):
    background = await auth_client.patch(
        "/api/v1/settings/background-ai",
        json={"enabled": True, "tasks": ["summarize", "suggest_links"]},
    )
    assert background.status_code == 200, background.text
    assert background.json()["enabled"] is True
    assert background.json()["tasks"] == ["summarize", "suggest_links"]

    mcp = await auth_client.patch(
        "/api/v1/settings/mcp",
        json={"web_search_threshold": 0.2, "web_search_connection_name": "Brave"},
    )
    assert mcp.status_code == 200, mcp.text
    assert mcp.json()["web_search_threshold"] == 0.2
    assert mcp.json()["web_search_connection_name"] == "Brave"

    settings_resp = await auth_client.get("/api/v1/settings")
    body = settings_resp.json()
    assert body["background_ai"]["tasks"] == ["summarize", "suggest_links"]
    assert body["mcp"]["web_search_threshold"] == 0.2


@pytest.mark.asyncio
async def test_settings_requires_auth_when_mobile_profile(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "kos_profile", "mobile")
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 401
