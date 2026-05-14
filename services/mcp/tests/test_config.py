from __future__ import annotations

from kos_mcp.config import DEFAULT_ALLOWED_TOOLS, McpSettings


def test_mcp_disabled_by_default() -> None:
    s = McpSettings()
    assert s.mcp_enabled is False


def test_write_tools_disabled_by_default() -> None:
    s = McpSettings()
    assert s.mcp_allow_write_tools is False


def test_file_access_disabled_by_default() -> None:
    s = McpSettings()
    assert s.mcp_allow_file_access is False


def test_empty_token_by_default() -> None:
    s = McpSettings()
    assert s.mcp_internal_token == ""


def test_default_allowed_tools_contains_expected() -> None:
    expected = {
        "search_objects",
        "hybrid_search",
        "get_object",
        "get_page",
        "get_source",
        "get_related_objects",
        "answer_from_kb",
    }
    assert expected == set(DEFAULT_ALLOWED_TOOLS)


def test_default_allowed_tools_in_settings() -> None:
    s = McpSettings()
    assert set(s.mcp_allowed_tools) == set(DEFAULT_ALLOWED_TOOLS)
