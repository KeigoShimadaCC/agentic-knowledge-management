"""Integration tests for Phase 12C AI augmentation (web search + enrich-page)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ─── helpers ────────────────────────────────────────────────────────────────


def _make_openai_mock(content: str = "Answer text. Sources: []") -> MagicMock:
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=content))]
    mock_completion.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
    client_mock = MagicMock()
    client_mock.chat = MagicMock()
    client_mock.chat.completions = MagicMock()
    client_mock.chat.completions.create = AsyncMock(return_value=mock_completion)
    return client_mock


def _make_search_result(score: float = 0.9) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.title = "Test KB Result"
    r.snippet = "A test snippet"
    r.score = score
    r.kind = "page"
    r.metadata_ = {}
    return r


def _make_mock_web_conn(tool_name: str = "brave_web_search") -> MagicMock:
    conn = MagicMock()
    conn.id = uuid.uuid4()
    conn.name = "Brave Search"
    conn.transport = "stdio"
    conn.command = "echo"
    conn.args = []
    conn.env_vars = {}
    conn.enabled = True
    conn.capabilities = [{"name": tool_name}]
    return conn


def _make_mcp_session_cm(return_value: dict) -> MagicMock:
    """Build an async context manager mock for McpClientSession."""
    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=return_value)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


BRAVE_RESULT = {
    "results": [
        {"title": "Web Result 1", "url": "https://example.com/1", "description": "A web page"},
        {"title": "Web Result 2", "url": "https://example.com/2", "description": "Another page"},
    ]
}

CONTEXT7_RESULT = {
    "results": [
        {
            "title": "FastAPI Docs",
            "url": "https://fastapi.tiangolo.com",
            "description": "FastAPI documentation",
        }
    ]
}


async def _make_page(auth_client: AsyncClient) -> dict:
    r = await auth_client.post("/api/v1/pages", json={"title": "Test Page"})
    assert r.status_code == 201
    return r.json()


# ─── /ai/answer web search tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_returns_new_fields_by_default(auth_client: AsyncClient):
    """With use_web_search omitted, response includes web_citations=[] and warning=null."""
    oai = _make_openai_mock()
    with patch("openai.AsyncOpenAI", return_value=oai):
        r = await auth_client.post("/api/v1/ai/answer", json={"q": "test question"})
    assert r.status_code == 200
    data = r.json()
    assert "web_citations" in data
    assert data["web_citations"] == []
    assert data.get("warning") is None


@pytest.mark.asyncio
async def test_answer_web_search_no_connection(auth_client: AsyncClient):
    """use_web_search=True but no MCP connection → warning='web_search_unavailable', no 500."""
    low_result = _make_search_result(score=0.1)
    oai = _make_openai_mock()
    with (
        patch("openai.AsyncOpenAI", return_value=oai),
        patch(
            "app.services.ai_service.hybrid_search",
            new=AsyncMock(return_value=([low_result], True)),
        ),
        patch(
            "app.services.mcp_connection_service.find_connection_for_patterns",
            new=AsyncMock(return_value=None),
        ),
    ):
        r = await auth_client.post(
            "/api/v1/ai/answer", json={"q": "test question", "use_web_search": True}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["warning"] == "web_search_unavailable"
    assert data["web_citations"] == []


@pytest.mark.asyncio
async def test_answer_web_search_high_kb_score_skips_mcp(auth_client: AsyncClient):
    """use_web_search=True but KB score is high → web search not triggered."""
    high_result = _make_search_result(score=0.9)
    find_conn = AsyncMock(return_value=_make_mock_web_conn())
    oai = _make_openai_mock()
    with (
        patch("openai.AsyncOpenAI", return_value=oai),
        patch(
            "app.services.ai_service.hybrid_search",
            new=AsyncMock(return_value=([high_result], True)),
        ),
        patch("app.services.mcp_connection_service.find_connection_for_patterns", new=find_conn),
    ):
        r = await auth_client.post(
            "/api/v1/ai/answer", json={"q": "test question", "use_web_search": True}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["web_citations"] == []
    assert data.get("warning") is None
    # find_connection should not have been called (high score)
    find_conn.assert_not_called()


@pytest.mark.asyncio
async def test_answer_web_search_populates_web_citations(auth_client: AsyncClient):
    """Low KB score + configured connection → web_citations populated."""
    low_result = _make_search_result(score=0.1)
    mock_conn = _make_mock_web_conn("brave_web_search")
    session_cm = _make_mcp_session_cm(BRAVE_RESULT)
    oai = _make_openai_mock()
    with (
        patch("openai.AsyncOpenAI", return_value=oai),
        patch(
            "app.services.ai_service.hybrid_search",
            new=AsyncMock(return_value=([low_result], True)),
        ),
        patch(
            "app.services.mcp_connection_service.find_connection_for_patterns",
            new=AsyncMock(return_value=mock_conn),
        ),
        patch("app.services.ai_service.McpClientSession", return_value=session_cm),
    ):
        r = await auth_client.post(
            "/api/v1/ai/answer", json={"q": "latest AI news", "use_web_search": True}
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data["web_citations"]) > 0
    assert data["web_citations"][0]["url"].startswith("https://")
    assert data.get("warning") is None


@pytest.mark.asyncio
async def test_answer_web_search_mcp_error_graceful(auth_client: AsyncClient):
    """McpClientSession raises → warning set, still 200 (no 500)."""
    from app.mcp_client.client import McpConnectionError

    low_result = _make_search_result(score=0.1)
    mock_conn = _make_mock_web_conn("brave_web_search")
    # Session that raises on call_tool
    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(side_effect=McpConnectionError("timeout"))
    failing_cm = MagicMock()
    failing_cm.__aenter__ = AsyncMock(return_value=mock_session)
    failing_cm.__aexit__ = AsyncMock(return_value=None)
    oai = _make_openai_mock()
    with (
        patch("openai.AsyncOpenAI", return_value=oai),
        patch(
            "app.services.ai_service.hybrid_search",
            new=AsyncMock(return_value=([low_result], True)),
        ),
        patch(
            "app.services.mcp_connection_service.find_connection_for_patterns",
            new=AsyncMock(return_value=mock_conn),
        ),
        patch("app.services.ai_service.McpClientSession", return_value=failing_cm),
    ):
        r = await auth_client.post(
            "/api/v1/ai/answer", json={"q": "failing query", "use_web_search": True}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["warning"] == "web_search_unavailable"
    assert data["web_citations"] == []


# ─── /ai/enrich-page tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrich_page_no_context7_connection(auth_client: AsyncClient):
    """No Context7 connection configured → 422."""
    page_data = await _make_page(auth_client)
    page_id = page_data["page"]["id"]
    with patch(
        "app.services.mcp_connection_service.find_connection_for_patterns",
        new=AsyncMock(return_value=None),
    ):
        r = await auth_client.post(
            "/api/v1/ai/enrich-page", json={"page_id": page_id, "query": "FastAPI"}
        )
    assert r.status_code == 422
    assert "no_context7_connection" in r.json()["detail"]


@pytest.mark.asyncio
async def test_enrich_page_success(auth_client: AsyncClient):
    """Context7 connection + successful MCP call → sources + edges created."""
    page_data = await _make_page(auth_client)
    page_id = page_data["page"]["id"]

    mock_conn = _make_mock_web_conn("context7_get_docs")
    mock_conn.capabilities = [{"name": "context7_get_docs"}]
    session_cm = _make_mcp_session_cm(CONTEXT7_RESULT)

    with (
        patch(
            "app.services.mcp_connection_service.find_connection_for_patterns",
            new=AsyncMock(return_value=mock_conn),
        ),
        patch("app.services.ai_service.McpClientSession", return_value=session_cm),
    ):
        r = await auth_client.post(
            "/api/v1/ai/enrich-page", json={"page_id": page_id, "query": "FastAPI"}
        )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["sources_created"], list)
    assert len(data["sources_created"]) > 0
    assert isinstance(data["edges_created"], list)
    assert len(data["edges_created"]) > 0
    assert "agent_run_id" in data


@pytest.mark.asyncio
async def test_enrich_page_wrong_user(auth_client: AsyncClient):
    """Page belongs to user A; user B cannot enrich → 404."""
    from app.main import app as fastapi_app

    page_data = await _make_page(auth_client)
    page_id = page_data["page"]["id"]

    # Create second user
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as other:
        await other.post(
            "/api/v1/auth/register",
            json={"email": "other@test.com", "password": "password123", "display_name": "Other"},
        )
        r = await other.post(
            "/api/v1/ai/enrich-page", json={"page_id": page_id, "query": "FastAPI"}
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_enrich_page_not_found(auth_client: AsyncClient):
    """Non-existent page_id → 404."""
    r = await auth_client.post(
        "/api/v1/ai/enrich-page",
        json={"page_id": str(uuid.uuid4()), "query": "FastAPI"},
    )
    assert r.status_code == 404
