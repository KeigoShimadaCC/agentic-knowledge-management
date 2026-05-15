from __future__ import annotations

from kos_mcp.config import DEFAULT_ALLOWED_TOOLS, READ_TOOLS, WRITE_TOOL_NAMES, McpSettings


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


def test_default_allowed_tools_contains_all_28_tools() -> None:
    """DEFAULT_ALLOWED_TOOLS includes 14 read tools + 14 write tools (Phase 9D added 7+8 career).

    Write tools are gated by mcp_allow_write_tools at registration time,
    not by exclusion from the allowed list.
    """
    original_read = {
        "search_objects", "hybrid_search", "get_object", "get_page",
        "get_source", "get_related_objects", "answer_from_kb",
    }
    career_read = {
        "get_project", "list_projects", "get_resume_bullet_set",
        "list_resume_bullet_sets", "get_interview_story",
        "list_interview_stories", "get_project_evidence",
    }
    all_read = original_read | career_read
    assert all_read == set(READ_TOOLS)
    original_write = {
        "create_page", "update_page", "create_edge",
        "archive_object", "ingest_url", "ingest_file",
    }
    career_write = {
        "create_project", "update_project", "archive_project",
        "link_to_project", "unlink_from_project", "extract_project",
        "generate_and_save_resume_bullets", "generate_and_save_interview_story",
    }
    assert WRITE_TOOL_NAMES == original_write | career_write
    assert set(DEFAULT_ALLOWED_TOOLS) == all_read | WRITE_TOOL_NAMES


def test_default_allowed_tools_in_settings() -> None:
    s = McpSettings()
    assert set(s.mcp_allowed_tools) == set(DEFAULT_ALLOWED_TOOLS)


def test_write_tool_flag_off_means_28_in_allowlist_but_only_14_registered() -> None:
    """With flag off, the allowlist has 28 entries but write tools are not registered."""
    s = McpSettings()
    assert s.mcp_allow_write_tools is False
    # All 28 are in the allowlist
    assert len(s.mcp_allowed_tools) == 28
    # Write tools are in the allowlist but gated by the flag
    for write_tool in WRITE_TOOL_NAMES:
        assert write_tool in s.mcp_allowed_tools
