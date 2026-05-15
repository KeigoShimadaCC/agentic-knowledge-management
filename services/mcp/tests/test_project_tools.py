from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from kos_mcp.client import KosApiClient
from kos_mcp.tools import (
    _archive_project,
    _create_project,
    _extract_project,
    _generate_and_save_interview_story,
    _generate_and_save_resume_bullets,
    _get_interview_story,
    _get_project,
    _get_project_evidence,
    _get_resume_bullet_set,
    _link_to_project,
    _list_interview_stories,
    _list_projects,
    _list_resume_bullet_sets,
    _unlink_from_project,
    _update_project,
)

# ── get_project ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_project_returns_compact(mock_client: KosApiClient) -> None:
    mock_client.get_project.return_value = {
        "id": "proj-1",
        "kind": "project",
        "title": "Build Platform",
        "role": "Senior Engineer",
        "organization": "Acme Corp",
        "period_start": "2023-01-01",
        "period_end": "2023-12-31",
        "status": "completed",
        "skills": ["Python", "Kubernetes"],
        "problem": "Slow deploys",
        "actions": "Migrated to K8s",
        "results": "10x faster",
        "metrics": {"deploy_time_reduction_pct": 90},
        "tags": ["infra"],
        "secret_field": "should not appear",
        "api_key": "sk-secret",
    }
    result = await _get_project(mock_client, project_id="proj-1")
    assert result["id"] == "proj-1"
    assert result["title"] == "Build Platform"
    assert result["role"] == "Senior Engineer"
    assert result["skills"] == ["Python", "Kubernetes"]
    assert result.get("api_key") != "sk-secret"
    assert "secret_field" not in result


@pytest.mark.asyncio
async def test_get_project_404_propagates(mock_client: KosApiClient) -> None:
    response = MagicMock()
    response.status_code = 404
    mock_client.get_project.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=response
    )
    with pytest.raises(httpx.HTTPStatusError):
        await _get_project(mock_client, project_id="nonexistent")


# ── list_projects ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_projects_forwards_filters(mock_client: KosApiClient) -> None:
    mock_client.list_projects.return_value = {
        "items": [
            {"id": "p1", "title": "T1", "role": "SWE", "organization": "Co",
             "status": "active", "period_start": None, "period_end": None, "skills": []},
        ],
        "total": 1,
    }
    result = await _list_projects(mock_client, status="active", skill="Python")
    mock_client.list_projects.assert_called_once_with(
        limit=20, offset=0, status="active", skill="Python"
    )
    assert result["items"][0]["id"] == "p1"
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_list_projects_handles_list_response(mock_client: KosApiClient) -> None:
    mock_client.list_projects.return_value = [
        {"id": "p2", "title": "T2", "role": None, "organization": None,
         "status": "paused", "period_start": None, "period_end": None, "skills": []}
    ]
    result = await _list_projects(mock_client)
    assert result["items"][0]["id"] == "p2"


# ── get_resume_bullet_set ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_resume_bullet_set_returns_bullets(mock_client: KosApiClient) -> None:
    mock_client.get_resume_bullet_set.return_value = {
        "id": "rbs-1",
        "project_id": "proj-1",
        "target_role": "Staff Engineer",
        "emphasis": "leadership",
        "count": 2,
        "bullets": [
            {
                "text": "Led migration",
                "confidence": "high",
                "evidence_object_ids": [],
                "metrics_cited": [],
            },
        ],
        "agent_run_id": "run-abc",
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
    }
    result = await _get_resume_bullet_set(mock_client, bullet_set_id="rbs-1")
    assert result["id"] == "rbs-1"
    assert result["target_role"] == "Staff Engineer"
    assert len(result["bullets"]) == 1


# ── list_resume_bullet_sets ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_resume_bullet_sets_paginates(mock_client: KosApiClient) -> None:
    mock_client.list_resume_bullet_sets.return_value = {"items": [], "total": 0}
    await _list_resume_bullet_sets(mock_client, project_id="proj-1", limit=5, offset=10)
    mock_client.list_resume_bullet_sets.assert_called_once_with(
        project_id="proj-1", limit=5, offset=10
    )


# ── get_interview_story ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_interview_story_returns_star(mock_client: KosApiClient) -> None:
    mock_client.get_interview_story.return_value = {
        "id": "story-1",
        "project_id": "proj-1",
        "question_type": "behavioral",
        "target_role": "EM",
        "max_words": 300,
        "word_count": 250,
        "story": {"situation": "S", "task": "T", "action": "A", "result": "R",
                  "evidence_object_ids": []},
        "agent_run_id": "run-xyz",
        "created_at": "2024-01-01",
        "updated_at": "2024-01-01",
    }
    result = await _get_interview_story(mock_client, story_id="story-1")
    assert result["id"] == "story-1"
    assert result["story"]["situation"] == "S"
    assert result["word_count"] == 250


# ── list_interview_stories ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_interview_stories_filters_question_type(mock_client: KosApiClient) -> None:
    mock_client.list_interview_stories.return_value = {"items": [], "total": 0}
    await _list_interview_stories(
        mock_client, project_id="proj-1", question_type="technical"
    )
    mock_client.list_interview_stories.assert_called_once_with(
        project_id="proj-1", question_type="technical", limit=20, offset=0
    )


# ── get_project_evidence ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_project_evidence_returns_compact_list(mock_client: KosApiClient) -> None:
    mock_client.get_project_evidence.return_value = [
        {"id": "obj-1", "kind": "page", "title": "RFC doc",
         "edge_kind": "belongs_to_project", "direction": "incoming", "deleted_at": None},
    ]
    result = await _get_project_evidence(mock_client, project_id="proj-1")
    assert len(result) == 1
    assert result[0]["id"] == "obj-1"
    assert result[0]["kind"] == "page"
    assert "deleted_at" not in result[0]


# ── create_project ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_project_rejects_empty_title(mock_client: KosApiClient) -> None:
    with pytest.raises(ValueError, match="title"):
        await _create_project(mock_client, title="   ")


@pytest.mark.asyncio
async def test_create_project_happy_path(mock_client: KosApiClient) -> None:
    mock_client.create_project.return_value = {
        "id": "proj-new",
        "kind": "project",
        "title": "New Project",
        "status": "active",
        "created_at": "2024-06-01",
    }
    result = await _create_project(
        mock_client,
        title="New Project",
        role="Backend Engineer",
        skills=["Python", "FastAPI"],
    )
    assert result["id"] == "proj-new"
    assert result["kind"] == "project"
    mock_client.create_project.assert_called_once()
    call_kwargs = mock_client.create_project.call_args.kwargs
    assert call_kwargs["title"] == "New Project"
    assert call_kwargs["role"] == "Backend Engineer"


# ── update_project ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_project_happy_path(mock_client: KosApiClient) -> None:
    mock_client.update_project.return_value = {
        "id": "proj-1",
        "title": "Updated",
        "status": "completed",
        "updated_at": "2024-07-01",
    }
    result = await _update_project(
        mock_client, project_id="proj-1", status="completed"
    )
    assert result["id"] == "proj-1"
    assert result["status"] == "completed"
    mock_client.update_project.assert_called_once_with(
        project_id="proj-1",
        title=None, description=None, period_start=None, period_end=None,
        role=None, organization=None, problem=None, actions=None, results=None,
        metrics=None, skills=None, status="completed", tags=None,
    )


# ── archive_project ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_project_calls_archive_object(mock_client: KosApiClient) -> None:
    mock_client.archive_object.return_value = {
        "id": "proj-1",
        "is_archived": True,
        "updated_at": "2024-07-01",
    }
    result = await _archive_project(mock_client, project_id="proj-1", reason="Done")
    assert result["is_archived"] is True
    mock_client.archive_object.assert_called_once_with(
        object_id="proj-1", reason="Done"
    )


# ── link_to_project ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_link_to_project_creates_belongs_to_edge(mock_client: KosApiClient) -> None:
    mock_client.create_edge.return_value = {
        "id": "edge-1",
        "source_id": "obj-a",
        "target_id": "proj-1",
        "kind": "belongs_to_project",
    }
    result = await _link_to_project(
        mock_client, object_id="obj-a", project_id="proj-1"
    )
    assert result["kind"] == "belongs_to_project"
    assert result["source_id"] == "obj-a"
    assert result["target_id"] == "proj-1"
    mock_client.create_edge.assert_called_once_with(
        source_id="obj-a", target_id="proj-1", kind="belongs_to_project"
    )


# ── unlink_from_project ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unlink_from_project_calls_delete_edge(mock_client: KosApiClient) -> None:
    mock_client.delete_edge.return_value = {}
    result = await _unlink_from_project(mock_client, edge_id="edge-1")
    assert result["deleted"] is True
    assert result["edge_id"] == "edge-1"
    mock_client.delete_edge.assert_called_once_with(edge_id="edge-1")


# ── extract_project ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extract_project_503_returns_error(mock_client: KosApiClient) -> None:
    response = MagicMock()
    response.status_code = 503
    response.text = "AI disabled"
    mock_client.extract_project.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=response
    )
    result = await _extract_project(mock_client, source_id="src-1")
    assert result["error"] == "ai_disabled"
    assert "OPENAI_API_KEY" in result["message"]


@pytest.mark.asyncio
async def test_extract_project_happy_path(mock_client: KosApiClient) -> None:
    mock_client.extract_project.return_value = {
        "project_id": "proj-new",
        "agent_run_id": "run-1",
        "source_id": "src-1",
        "draft": {"title": "Extracted Project"},
    }
    result = await _extract_project(mock_client, source_id="src-1")
    assert result["project_id"] == "proj-new"
    assert result["source_id"] == "src-1"
    mock_client.extract_project.assert_called_once_with(
        source_id="src-1", create=True, period_hint=None
    )


# ── generate_and_save_resume_bullets ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_and_save_resume_bullets_happy_path(
    mock_client: KosApiClient,
) -> None:
    mock_client.generate_resume_bullets.return_value = {
        "project_id": "proj-1",
        "bullets": [
            {"text": "Led infra migration", "confidence": "high",
             "evidence_object_ids": [], "metrics_cited": ["10x"]},
        ],
        "agent_run_id": "run-gen",
        "evidence_count": 3,
    }
    mock_client.save_resume_bullet_set.return_value = {
        "id": "rbs-saved",
        "project_id": "proj-1",
    }
    result = await _generate_and_save_resume_bullets(
        mock_client, project_id="proj-1", target_role="SRE", count=1
    )
    assert result["id"] == "rbs-saved"
    assert result["count"] == 1
    assert result["agent_run_id"] == "run-gen"
    mock_client.generate_resume_bullets.assert_called_once()
    mock_client.save_resume_bullet_set.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_save_resume_bullets_503_returns_error(
    mock_client: KosApiClient,
) -> None:
    response = MagicMock()
    response.status_code = 503
    mock_client.generate_resume_bullets.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=response
    )
    result = await _generate_and_save_resume_bullets(
        mock_client, project_id="proj-1"
    )
    assert result["error"] == "ai_disabled"
    mock_client.save_resume_bullet_set.assert_not_called()


# ── generate_and_save_interview_story ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_and_save_interview_story_happy_path(
    mock_client: KosApiClient,
) -> None:
    mock_client.generate_interview_story.return_value = {
        "project_id": "proj-1",
        "story": {"situation": "S", "task": "T", "action": "A", "result": "R",
                  "evidence_object_ids": []},
        "agent_run_id": "run-gen-s",
        "word_count": 200,
    }
    mock_client.save_interview_story.return_value = {
        "id": "story-saved",
        "project_id": "proj-1",
    }
    result = await _generate_and_save_interview_story(
        mock_client, project_id="proj-1", question_type="behavioral", max_words=300
    )
    assert result["id"] == "story-saved"
    assert result["word_count"] == 200
    assert result["story"]["situation"] == "S"
    mock_client.generate_interview_story.assert_called_once()
    mock_client.save_interview_story.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_save_interview_story_503_returns_error(
    mock_client: KosApiClient,
) -> None:
    response = MagicMock()
    response.status_code = 503
    mock_client.generate_interview_story.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=response
    )
    result = await _generate_and_save_interview_story(
        mock_client, project_id="proj-1"
    )
    assert result["error"] == "ai_disabled"
    mock_client.save_interview_story.assert_not_called()
