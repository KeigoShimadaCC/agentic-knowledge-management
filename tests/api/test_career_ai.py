"""Integration tests for Phase 9B career AI generators."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _make_openai_mock(content: str) -> MagicMock:
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=content))]
    mock_completion.usage = MagicMock(prompt_tokens=11, completion_tokens=22)

    client_mock = MagicMock()
    client_mock.chat = MagicMock()
    client_mock.chat.completions = MagicMock()
    client_mock.chat.completions.create = AsyncMock(return_value=mock_completion)
    return client_mock


def _resume_json(count: int = 3) -> str:
    return json.dumps(
        {
            "bullets": [
                {
                    "text": (
                        f"Built reliable project workflow {i} that reduced "
                        f"review time by 40 percent."
                    ),
                    "evidence_object_ids": [],
                    "confidence": "medium",
                    "metrics_cited": ["review_time"],
                }
                for i in range(count)
            ]
        }
    )


def _story_json() -> str:
    return json.dumps(
        {
            "situation": "The team needed a clearer way to capture career project evidence.",
            "task": "I had to turn scattered work notes into structured project memory.",
            "action": (
                "I designed backend endpoints, linked evidence records, "
                "and kept the workflow auditable."
            ),
            "result": (
                "The system produced reusable project summaries for "
                "resume and interview preparation."
            ),
            "evidence_object_ids": [],
        }
    )


async def _make_page(auth_client: AsyncClient, title: str, content: str | None = None) -> dict:
    resp = await auth_client.post("/api/v1/pages", json={"title": title})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    page_id = data["page"]["id"]
    await auth_client.patch(
        f"/api/v1/pages/{page_id}",
        json={"content_text": content or f"{title} evidence text with measurable impact."},
    )
    return data


async def _make_project(auth_client: AsyncClient, *, extracted_from: str | None = None) -> dict:
    body = {
        "title": "Career Project",
        "description": "Built career memory generators.",
        "role": "Backend Engineer",
        "organization": "KnowledgeOS",
        "problem": "Project evidence was scattered.",
        "actions": "Designed APIs and evidence collection.",
        "results": "Reduced resume preparation time by 40 percent.",
        "metrics": {"review_time": "40 percent reduction"},
        "skills": ["python", "fastapi"],
    }
    if extracted_from is not None:
        body["extracted_from"] = extracted_from
    resp = await auth_client.post("/api/v1/projects", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _link_evidence(auth_client: AsyncClient, *, source_id: str, project_id: str) -> None:
    resp = await auth_client.post(
        "/api/v1/edges",
        json={
            "source_id": source_id,
            "target_id": project_id,
            "kind": "belongs_to_project",
        },
    )
    assert resp.status_code in {200, 201}, resp.text


async def _agent_run_count() -> int:
    from app.db.session import engine
    from app.models.agent_run import AgentRun
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as session:
        result = await session.execute(select(func.count()).select_from(AgentRun))
        return int(result.scalar() or 0)


async def _latest_run(agent_type: str):
    from app.db.session import engine
    from app.models.agent_run import AgentRun
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(AgentRun)
            .where(AgentRun.agent_type == agent_type)
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_generate_resume_bullets_happy_path_with_evidence(auth_client: AsyncClient):
    source = await _make_page(auth_client, "Original project notes")
    project = await _make_project(auth_client, extracted_from=source["object"]["id"])
    for title in ("Launch notes", "Metrics notes"):
        page = await _make_page(auth_client, title)
        await _link_evidence(auth_client, source_id=page["object"]["id"], project_id=project["id"])

    client_mock = _make_openai_mock(_resume_json(3))
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 3},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["bullets"]) == 3
    assert all(b["text"] for b in data["bullets"])
    assert data["evidence_count"] == 3
    assert data["agent_run_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 5])
async def test_generate_resume_bullets_count_bounds(auth_client: AsyncClient, count: int):
    project = await _make_project(auth_client)
    client_mock = _make_openai_mock(_resume_json(count))
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": count},
        )

    assert resp.status_code == 200, resp.text
    assert len(resp.json()["bullets"]) == count


@pytest.mark.asyncio
async def test_generate_resume_bullets_rejects_count_above_limit(auth_client: AsyncClient):
    project = await _make_project(auth_client)
    resp = await auth_client.post(
        "/api/v1/ai/generate-resume-bullets",
        json={"project_id": project["id"], "count": 6},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_resume_bullets_project_not_owned(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@test.com", "password": "password123", "display_name": "Owner"},
    )
    project = await _make_project(client)

    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@test.com", "password": "password123", "display_name": "Other"},
    )
    client_mock = _make_openai_mock(_resume_json(1))
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 1},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_resume_bullets_project_soft_deleted(auth_client: AsyncClient):
    project = await _make_project(auth_client)
    delete = await auth_client.delete(f"/api/v1/projects/{project['id']}")
    assert delete.status_code == 204

    client_mock = _make_openai_mock(_resume_json(1))
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 1},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_resume_bullets_ai_disabled_no_agent_run(auth_client: AsyncClient):
    from app.ai import providers as providers_module

    project = await _make_project(auth_client)
    before = await _agent_run_count()
    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 1},
        )

    assert resp.status_code == 503
    assert await _agent_run_count() == before


@pytest.mark.asyncio
async def test_generate_resume_bullets_malformed_json_persists_failed_run(
    auth_client: AsyncClient,
):
    project = await _make_project(auth_client)
    client_mock = _make_openai_mock("NOT VALID JSON {{{")
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 1},
        )

    assert resp.status_code == 502
    run = await _latest_run("generate_resume_bullets")
    assert run is not None
    assert run.status == "failed"
    assert run.output == {"text": "NOT VALID JSON {{{"}


@pytest.mark.asyncio
async def test_generate_interview_story_happy_path(auth_client: AsyncClient):
    source = await _make_page(auth_client, "Story source")
    project = await _make_project(auth_client)
    await _link_evidence(auth_client, source_id=source["object"]["id"], project_id=project["id"])

    client_mock = _make_openai_mock(_story_json())
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-interview-story",
            json={"project_id": project["id"]},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["story"]["situation"]
    assert data["story"]["task"]
    assert data["story"]["action"]
    assert data["story"]["result"]
    assert 1 <= data["word_count"] <= 600


@pytest.mark.asyncio
async def test_generate_interview_story_accepts_technical_prompt(auth_client: AsyncClient):
    project = await _make_project(auth_client)
    client_mock = _make_openai_mock(_story_json())
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-interview-story",
            json={"project_id": project["id"], "question_type": "technical"},
        )

    assert resp.status_code == 200, resp.text
    kwargs = client_mock.chat.completions.create.await_args.kwargs
    system_prompt = kwargs["messages"][0]["content"]
    assert 'question_type "technical"' in system_prompt
    assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_generate_interview_story_max_words_100(auth_client: AsyncClient):
    project = await _make_project(auth_client)
    client_mock = _make_openai_mock(_story_json())
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-interview-story",
            json={"project_id": project["id"], "max_words": 100},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["word_count"] <= 150


@pytest.mark.asyncio
async def test_generate_interview_story_ai_disabled(auth_client: AsyncClient):
    from app.ai import providers as providers_module

    project = await _make_project(auth_client)
    with patch.object(providers_module.settings, "openai_api_key", ""):
        resp = await auth_client.post(
            "/api/v1/ai/generate-interview-story",
            json={"project_id": project["id"]},
        )

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_career_ai_evidence_cap(auth_client: AsyncClient):
    original = await _make_page(auth_client, "Original source")
    project = await _make_project(auth_client, extracted_from=original["object"]["id"])
    for i in range(15):
        page = await _make_page(auth_client, f"Evidence {i}")
        await _link_evidence(auth_client, source_id=page["object"]["id"], project_id=project["id"])

    client_mock = _make_openai_mock(_resume_json(1))
    with patch("openai.AsyncOpenAI", return_value=client_mock):
        resp = await auth_client.post(
            "/api/v1/ai/generate-resume-bullets",
            json={"project_id": project["id"], "count": 1, "max_evidence_objects": 5},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["evidence_count"] == 5
    kwargs = client_mock.chat.completions.create.await_args.kwargs
    user_payload = json.loads(kwargs["messages"][1]["content"])
    assert len(user_payload["evidence"]) == 5
