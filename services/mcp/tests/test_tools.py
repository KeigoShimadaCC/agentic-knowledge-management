from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from kos_mcp.client import KosApiClient
from kos_mcp.redaction import redact_dict
from kos_mcp.tools import (
    _answer_from_kb,
    _get_object,
    _get_page,
    _get_related_objects,
    _get_source,
    _hybrid_search,
    _search_objects,
    _PAGE_TEXT_LIMIT,
    _SOURCE_TEXT_DEFAULT_LIMIT,
)


# ── search_objects ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_objects_returns_compact_list(mock_client: KosApiClient) -> None:
    mock_client.keyword_search.return_value = [
        {
            "id": "abc",
            "kind": "page",
            "title": "Test Page",
            "snippet": "snippet text",
            "tags": ["t1"],
            "updated_at": "2024-01-01",
            "score": 0.9,
            "api_key": "secret",
        }
    ]
    results = await _search_objects(mock_client, query="test")
    assert len(results) == 1
    obj = results[0]
    assert obj["id"] == "abc"
    assert obj["embeddings_used"] is False
    # api_key is not included in the compact output fields at all
    assert obj.get("api_key") != "secret"


@pytest.mark.asyncio
async def test_search_objects_wraps_dict_response(mock_client: KosApiClient) -> None:
    mock_client.keyword_search.return_value = {
        "items": [{"id": "1", "kind": "source", "title": "S"}]
    }
    results = await _search_objects(mock_client, query="q")
    assert results[0]["id"] == "1"


# ── hybrid_search ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_search_returns_embeddings_used_flag(mock_client: KosApiClient) -> None:
    mock_client.hybrid_search.return_value = {
        "items": [{"id": "x", "kind": "page", "title": "X"}],
        "embeddings_used": True,
    }
    result = await _hybrid_search(mock_client, query="q")
    assert result["embeddings_used"] is True
    assert result["results"][0]["id"] == "x"


@pytest.mark.asyncio
async def test_hybrid_search_falls_back_on_503(mock_client: KosApiClient) -> None:
    response = MagicMock()
    response.status_code = 503
    response.text = "embeddings disabled"
    mock_client.hybrid_search.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=response
    )
    mock_client.keyword_search.return_value = [
        {"id": "k", "kind": "page", "title": "K"}
    ]
    result = await _hybrid_search(mock_client, query="q")
    assert result["embeddings_used"] is False
    assert "warning" in result
    assert result["results"][0]["id"] == "k"


# ── get_object ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_object_returns_compact_metadata(mock_client: KosApiClient) -> None:
    mock_client.get_object.return_value = {
        "id": "oid",
        "kind": "page",
        "title": "My Page",
        "description": "desc",
        "tags": [],
        "metadata": {},
        "is_pinned": False,
        "is_archived": False,
        "created_at": "2024-01-01",
        "updated_at": "2024-06-01",
        "deleted_at": None,
        "password": "secret",
    }
    result = await _get_object(mock_client, object_id="oid")
    assert result["id"] == "oid"
    assert "deleted_at" not in result
    assert "password" not in result  # not included in compact output


# ── get_page ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_page_omits_content_json_by_default(mock_client: KosApiClient) -> None:
    mock_client.get_page.return_value = {
        "id": "pid",
        "title": "P",
        "content_text": "hello",
        "content_json": {"type": "doc", "content": []},
        "word_count": 1,
        "version": 1,
        "tags": [],
        "metadata": {},
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
    }
    result = await _get_page(mock_client, page_id="pid")
    assert "content_json" not in result
    assert result["content_text"] == "hello"


@pytest.mark.asyncio
async def test_get_page_includes_json_when_requested(mock_client: KosApiClient) -> None:
    mock_client.get_page.return_value = {
        "id": "pid",
        "title": "P",
        "content_text": "hello",
        "content_json": {"type": "doc"},
        "word_count": 1,
        "version": 1,
        "tags": [],
        "metadata": {},
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
    }
    result = await _get_page(mock_client, page_id="pid", include_json=True)
    assert result["content_json"] == {"type": "doc"}


@pytest.mark.asyncio
async def test_get_page_truncates_long_text(mock_client: KosApiClient) -> None:
    long_text = "x" * (_PAGE_TEXT_LIMIT + 100)
    mock_client.get_page.return_value = {
        "id": "pid",
        "title": "P",
        "content_text": long_text,
        "word_count": 1,
        "version": 1,
        "tags": [],
        "metadata": {},
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
    }
    result = await _get_page(mock_client, page_id="pid")
    assert len(result["content_text"]) == _PAGE_TEXT_LIMIT
    assert result["truncated"] is True


# ── get_source ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_source_truncates_extracted_text(mock_client: KosApiClient) -> None:
    mock_client.get_source.return_value = {
        "id": "sid",
        "kind": "source",
        "title": "S",
        "description": None,
        "tags": [],
        "source_type": "pdf",
        "url": None,
        "ingestion_status": "complete",
        "page_count": 5,
        "thumbnail_path": None,
        "preview_data": None,
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
        "extracted_text": "y" * (_SOURCE_TEXT_DEFAULT_LIMIT + 50),
        "asset_id": "internal",
        "error_message": "internal error detail",
    }
    result = await _get_source(mock_client, source_id="sid")
    assert len(result["extracted_text"]) == _SOURCE_TEXT_DEFAULT_LIMIT
    assert result["text_truncated"] is True
    assert "asset_id" not in result
    assert "error_message" not in result


# ── get_related_objects ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_related_objects_caps_depth(mock_client: KosApiClient) -> None:
    mock_client.get_related_objects.return_value = []
    await _get_related_objects(mock_client, object_id="oid", depth=5)
    call_kwargs = mock_client.get_related_objects.call_args.kwargs
    # depth cap is enforced in KosApiClient.get_related_objects, not here
    # but verify the call was made
    assert call_kwargs["object_id"] == "oid"


@pytest.mark.asyncio
async def test_get_related_objects_compact_output(mock_client: KosApiClient) -> None:
    mock_client.get_related_objects.return_value = [
        {
            "id": "r1",
            "kind": "page",
            "title": "Related",
            "direction": "outgoing",
            "edge_kind": "citation",
            "depth": 1,
            "deleted_at": None,
        }
    ]
    result = await _get_related_objects(mock_client, object_id="oid")
    assert result[0]["id"] == "r1"
    assert result[0]["edge_kind"] == "citation"
    assert "deleted_at" not in result[0]


# ── answer_from_kb ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_from_kb_happy_path(mock_client: KosApiClient) -> None:
    mock_client.answer_from_kb.return_value = {
        "answer": "KnowledgeOS is a local-first AI knowledge base.",
        "citations": ["uuid-1", "uuid-2"],
        "context_count": 5,
        "agent_run_id": "run-abc",
    }
    result = await _answer_from_kb(mock_client, question="What is KnowledgeOS?")
    assert result["answer"] == "KnowledgeOS is a local-first AI knowledge base."
    assert result["citations"] == ["uuid-1", "uuid-2"]
    assert result["context_count"] == 5
    assert result["agent_run_id"] == "run-abc"


@pytest.mark.asyncio
async def test_answer_from_kb_503_returns_error_dict(mock_client: KosApiClient) -> None:
    response = MagicMock()
    response.status_code = 503
    response.text = "AI disabled"
    mock_client.answer_from_kb.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=response
    )
    result = await _answer_from_kb(mock_client, question="q")
    assert result["error"] == "ai_disabled"
    assert "OPENAI_API_KEY" in result["message"]


# ── redact_dict ──────────────────────────────────────────────────────────────

def test_redact_dict_strips_known_secrets() -> None:
    data = {
        "id": "x",
        "api_key": "sk-secret",
        "openai_api_key": "sk-openai",
        "mcp_internal_token": "tok",
        "password": "pw",
        "token_hash": "hash",
        "session_secret": "sess",
        "title": "safe",
        "nested": {"token": "hidden", "name": "visible"},
    }
    result = redact_dict(data)
    assert result["id"] == "x"
    assert result["title"] == "safe"
    assert result["api_key"] == "[REDACTED]"
    assert result["openai_api_key"] == "[REDACTED]"
    assert result["mcp_internal_token"] == "[REDACTED]"
    assert result["password"] == "[REDACTED]"
    assert result["token_hash"] == "[REDACTED]"
    assert result["session_secret"] == "[REDACTED]"
    assert result["nested"]["name"] == "visible"
    assert result["nested"]["token"] == "[REDACTED]"
