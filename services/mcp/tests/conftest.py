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
    return client
