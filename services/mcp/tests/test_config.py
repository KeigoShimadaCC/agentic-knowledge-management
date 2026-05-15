from __future__ import annotations

from kos_mcp.config import DEFAULT_ALLOWED_TOOLS, McpSettings, READ_TOOLS, WRITE_TOOL_NAMES


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


def test_default_allowed_tools_contains_all_13_tools() -> None:
    """DEFAULT_ALLOWED_TOOLS now includes 7 read tools + 6 write tools.

    Write tools are gated by mcp_allow_write_tools at registration time,
    not by exclusion from the allowed list.
    """
    read_tools = {
        "search_objects",
        "hybrid_search",
        "get_object",
        "get_page",
        "get_source",
        "get_related_objects",
        "answer_from_kb",
    }
    assert read_tools == set(READ_TOOLS)
    assert WRITE_TOOL_NAMES == {
        "create_page", "update_page", "create_edge",
        "archive_object", "ingest_url", "ingest_file",
    }
    assert set(DEFAULT_ALLOWED_TOOLS) == read_tools | WRITE_TOOL_NAMES


def test_default_allowed_tools_in_settings() -> None:
    s = McpSettings()
    assert set(s.mcp_allowed_tools) == set(DEFAULT_ALLOWED_TOOLS)


def test_write_tool_flag_off_means_13_in_allowlist_but_only_7_registered() -> None:
    """With flag off, the allowlist has 13 entries but write tools are not registered."""
    s = McpSettings()
    assert s.mcp_allow_write_tools is False
    # All 13 are in the allowlist
    assert len(s.mcp_allowed_tools) == 13
    # Write tools are in the allowlist but gated by the flag
    for write_tool in WRITE_TOOL_NAMES:
        assert write_tool in s.mcp_allowed_tools
