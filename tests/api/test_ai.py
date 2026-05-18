"""Integration tests for Phase 5 AI endpoints.

OpenAI calls are patched via unittest.mock — no real API calls are made.
conftest sets OPENAI_API_KEY=sk-test-placeholder before app imports so
settings.openai_api_key is non-empty for all tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _make_openai_mock(content: str = "Test summary.") -> MagicMock:
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


@pytest.fixture
def mock_openai_json():
    """Patch openai.AsyncOpenAI returning JSON for extract/suggest/triage."""
    content = (
        '[{"text": "Python is fast", "confidence": "high"},'
        ' {"text": "Guido created Python", "confidence": "high"}]'
    )
    client_mock = _make_openai_mock(content)
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        yield client_mock


async def _make_page(auth_client: AsyncClient, title: str = "Test Page") -> dict:
    r = await auth_client.post("/api/v1/pages", json={"title": title})
    assert r.status_code == 201, f"page create failed: {r.status_code} {r.text}"
    data = r.json()
    page_id = data["page"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": "Python was created by Guido van Rossum in 1991."},
    )
    return data


@pytest.mark.asyncio
async def test_summarize_page(auth_client: AsyncClient, mock_openai: MagicMock):
    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "Test summary."
    assert "agent_run_id" in data
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_summarize_cached(auth_client: AsyncClient, mock_openai: MagicMock):
    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    r1 = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert r1.status_code == 200
    assert r1.json()["cached"] is False

    r2 = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert r2.status_code == 200
    assert r2.json()["cached"] is True


@pytest.mark.asyncio
async def test_summarize_force_refresh(auth_client: AsyncClient, mock_openai: MagicMock):
    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    r2 = await auth_client.post(
        "/api/v1/ai/summarize", json={"object_id": object_id, "force": True}
    )
    assert r2.status_code == 200
    assert r2.json()["cached"] is False


@pytest.mark.asyncio
async def test_summarize_no_key(auth_client: AsyncClient):
    """Verify the endpoint returns 503 when OPENAI_API_KEY is empty."""
    from app.ai import providers as providers_module

    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]
    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_summarize_not_found(auth_client: AsyncClient, mock_openai: MagicMock):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": fake_id})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extract_claims(auth_client: AsyncClient, mock_openai_json: MagicMock):
    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/extract-claims", json={"object_id": object_id})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "agent_run_id" in data
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert "id" in item and "title" in item


@pytest.mark.asyncio
async def test_extract_tasks(auth_client: AsyncClient):
    task_json = '[{"title": "Review the proposal by Friday"}, {"title": "Schedule meeting"}]'
    client_mock = _make_openai_mock(task_json)
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        page_data = await _make_page(auth_client)
        object_id = page_data["object"]["id"]

        resp = await auth_client.post("/api/v1/ai/extract-tasks", json={"object_id": object_id})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_suggest_links_returns_no_crash(auth_client: AsyncClient):
    client_mock = _make_openai_mock("[]")
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        page_data = await _make_page(auth_client)
        object_id = page_data["object"]["id"]

        resp = await auth_client.post("/api/v1/ai/suggest-links", json={"object_id": object_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data and "agent_run_id" in data


@pytest.mark.asyncio
async def test_answer_question(auth_client: AsyncClient, mock_openai: MagicMock):
    resp = await auth_client.post("/api/v1/ai/answer", json={"q": "What is Python?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert "agent_run_id" in data
    assert "context_count" in data


@pytest.mark.asyncio
async def test_triage_returns_suggestions(auth_client: AsyncClient):
    triage_json = (
        '{"suggested_tags": ["python", "programming"],'
        ' "suggested_title": "Python Guide", "summary": "A page about Python."}'
    )
    client_mock = _make_openai_mock(triage_json)
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        page_data = await _make_page(auth_client)
        object_id = page_data["object"]["id"]

        resp = await auth_client.post("/api/v1/ai/triage", json={"object_id": object_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "suggested_tags" in data
        assert "summary" in data
        assert "agent_run_id" in data


@pytest.mark.asyncio
async def test_inbox_returns_untagged(auth_client: AsyncClient):
    await auth_client.post("/api/v1/pages", json={"title": "Untagged Page"})
    resp = await auth_client.get("/api/v1/ai/inbox")
    assert resp.status_code == 200
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert "Untagged Page" in titles


@pytest.mark.asyncio
async def test_inbox_excludes_tagged(auth_client: AsyncClient):
    r = await auth_client.post("/api/v1/pages", json={"title": "Tagged Page"})
    object_id = r.json()["object"]["id"]
    await auth_client.patch(f"/api/v1/objects/{object_id}", json={"tags": ["python"]})

    resp = await auth_client.get("/api/v1/ai/inbox")
    titles = [item["title"] for item in resp.json()["items"]]
    assert "Tagged Page" not in titles


@pytest.mark.asyncio
async def test_ai_writes_agent_run_row(auth_client: AsyncClient, mock_openai: MagicMock):
    from app.db.session import engine
    from app.models.agent_run import AgentRun
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/summarize", json={"object_id": object_id})
    assert resp.status_code == 200
    run_id = resp.json()["agent_run_id"]

    async with AsyncSession(engine) as session:
        result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
        row = result.scalar_one_or_none()

    assert row is not None
    assert row.agent_type == "summarize"
    assert row.status == "success"


@pytest.mark.asyncio
async def test_extract_creates_edges(auth_client: AsyncClient, mock_openai_json: MagicMock):
    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]

    resp = await auth_client.post("/api/v1/ai/extract-claims", json={"object_id": object_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0

    edges_resp = await auth_client.get(f"/api/v1/edges?source_id={object_id}")
    assert edges_resp.status_code == 200
    edge_targets = {e["target_id"] for e in edges_resp.json()}
    for item in items:
        assert item["id"] in edge_targets


def _extract_project_json() -> str:
    import json

    return json.dumps(
        {
            "title": "Shipped Feature X",
            "description": "One line summary for tests.",
            "period_start": None,
            "period_end": None,
            "role": "IC Engineer",
            "organization": "TestCo",
            "problem": "Slow queries hurt UX.",
            "actions": "Added indexes and caching.",
            "results": "50% faster page loads.",
            "metrics": {"p50_ms": 120},
            "skills": ["Python", "postgres"],
            "confidence": 0.88,
        }
    )


@pytest.fixture
def mock_openai_extract():
    client_mock = _make_openai_mock(_extract_project_json())
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        yield client_mock


@pytest.mark.asyncio
async def test_extract_project_from_page(auth_client: AsyncClient, mock_openai_extract: MagicMock):
    page_data = await _make_page(auth_client, title="Career Page")
    object_id = page_data["object"]["id"]

    resp = await auth_client.post(
        "/api/v1/ai/extract-project",
        json={"source_id": object_id, "create": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_id"] == object_id
    assert data["project_id"] is not None
    assert data["draft"]["title"] == "Shipped Feature X"
    assert data["draft"]["skills"] == ["python", "postgres"]

    from app.db.session import engine
    from app.models.agent_run import AgentRun
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as session:
        result = await session.execute(select(AgentRun).where(AgentRun.id == data["agent_run_id"]))
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.agent_type == "extract-project"
    assert row.status == "success"


@pytest.mark.asyncio
async def test_extract_project_dry_run(auth_client: AsyncClient, mock_openai_extract: MagicMock):
    page_data = await _make_page(auth_client, title="Dry Run Page")
    object_id = page_data["object"]["id"]

    before = await auth_client.get("/api/v1/projects?limit=100")
    n_before = before.json()["total"]

    resp = await auth_client.post(
        "/api/v1/ai/extract-project",
        json={"source_id": object_id, "create": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] is None
    assert data["draft"]["title"] == "Shipped Feature X"

    after = await auth_client.get("/api/v1/projects?limit=100")
    assert after.json()["total"] == n_before


@pytest.mark.asyncio
async def test_extract_project_invalid_kind(
    auth_client: AsyncClient, mock_openai_extract: MagicMock
):
    upload = await auth_client.post(
        "/api/v1/assets/upload",
        files={"file": ("blob.bin", b"not a project source", "application/octet-stream")},
    )
    assert upload.status_code == 201
    asset_id = upload.json()["object"]["id"]

    resp = await auth_client.post(
        "/api/v1/ai/extract-project",
        json={"source_id": asset_id, "create": True},
    )
    assert resp.status_code == 400
    assert "page, chat, or source" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_project_ai_disabled(auth_client: AsyncClient):
    from app.ai import providers as providers_module

    page_data = await _make_page(auth_client)
    object_id = page_data["object"]["id"]
    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post(
            "/api/v1/ai/extract-project",
            json={"source_id": object_id, "create": True},
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_extract_project_malformed_json(auth_client: AsyncClient):
    client_mock = _make_openai_mock("NOT VALID JSON {{{")
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        page_data = await _make_page(auth_client)
        object_id = page_data["object"]["id"]

        resp = await auth_client.post(
            "/api/v1/ai/extract-project",
            json={"source_id": object_id, "create": True},
        )
    assert resp.status_code == 502
    assert "malformed" in resp.json()["detail"].lower()

    from app.db.session import engine
    from app.models.agent_run import AgentRun
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(AgentRun)
            .where(AgentRun.agent_type == "extract-project")
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
    assert row is not None
    assert row.status == "failed"


# ── Workspace-scoped AI answer test ───────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_with_object_ids_scoped_to_workspace(
    auth_client: AsyncClient,
    mock_openai: MagicMock,
) -> None:
    """POST /ai/answer with object_ids only retrieves answers from scoped objects."""
    page_data = await _make_page(auth_client, title="Scoped workspace test page")
    object_id = page_data["object"]["id"]

    with patch("openai.AsyncOpenAI", return_value=mock_openai):
        resp = await auth_client.post(
            "/api/v1/ai/answer",
            json={"q": "What is in this workspace?", "object_ids": [object_id]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)


@pytest.mark.asyncio
async def test_answer_with_empty_object_ids_returns_answer(
    auth_client: AsyncClient,
    mock_openai: MagicMock,
) -> None:
    """POST /ai/answer with object_ids=[] behaves like no filter (null)."""
    with patch("openai.AsyncOpenAI", return_value=mock_openai):
        resp = await auth_client.post(
            "/api/v1/ai/answer",
            json={"q": "Generic question", "object_ids": None},
        )
    assert resp.status_code == 200
    assert "answer" in resp.json()
