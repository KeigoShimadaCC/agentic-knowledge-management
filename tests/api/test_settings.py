from __future__ import annotations

import pytest
from app.ai.providers import ANTHROPIC_TEST_STUB_KEY, TEST_STUB_SUMMARY
from app.config import settings
from httpx import AsyncClient


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
    assert ai_resp.json()["summary"] == TEST_STUB_SUMMARY


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
    assert ai_resp.json()["summary"] == TEST_STUB_SUMMARY


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
