from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from kos_mcp.client import KosApiClient
from kos_mcp.config import McpSettings


@pytest.fixture
def settings() -> McpSettings:
    return McpSettings(
        mcp_enabled=True,
        mcp_api_base_url="http://localhost:8000",
        mcp_internal_token="test-token",
    )


@pytest.fixture
def mock_client() -> KosApiClient:
    client = MagicMock(spec=KosApiClient)
    client.keyword_search = AsyncMock()
    client.hybrid_search = AsyncMock()
    client.get_object = AsyncMock()
    client.get_page = AsyncMock()
    client.get_source = AsyncMock()
    client.get_related_objects = AsyncMock()
    client.answer_from_kb = AsyncMock()
    # Write methods
    client.create_page = AsyncMock()
    client.update_page = AsyncMock()
    client.create_edge = AsyncMock()
    client.archive_object = AsyncMock()
    client.ingest_url = AsyncMock()
    client.ingest_file = AsyncMock()
    # Career / Project methods (Phase 9D)
    client.get_project = AsyncMock()
    client.list_projects = AsyncMock()
    client.create_project = AsyncMock()
    client.update_project = AsyncMock()
    client.get_resume_bullet_set = AsyncMock()
    client.list_resume_bullet_sets = AsyncMock()
    client.save_resume_bullet_set = AsyncMock()
    client.get_interview_story = AsyncMock()
    client.list_interview_stories = AsyncMock()
    client.save_interview_story = AsyncMock()
    client.get_project_evidence = AsyncMock()
    client.delete_edge = AsyncMock()
    client.extract_project = AsyncMock()
    client.generate_resume_bullets = AsyncMock()
    client.generate_interview_story = AsyncMock()
    return client
