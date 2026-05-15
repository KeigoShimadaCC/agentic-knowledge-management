from pydantic import Field
from pydantic_settings import BaseSettings

READ_TOOLS: list[str] = [
    "search_objects",
    "hybrid_search",
    "get_object",
    "get_page",
    "get_source",
    "get_related_objects",
    "answer_from_kb",
    # Career / Project read tools (Phase 9D)
    "get_project",
    "list_projects",
    "get_resume_bullet_set",
    "list_resume_bullet_sets",
    "get_interview_story",
    "list_interview_stories",
    "get_project_evidence",
]

WRITE_TOOLS: list[str] = [
    "create_page",
    "update_page",
    "create_edge",
    "archive_object",
    "ingest_url",
    "ingest_file",
    # Career / Project write tools (Phase 9D)
    "create_project",
    "update_project",
    "archive_project",
    "link_to_project",
    "unlink_from_project",
    "extract_project",
    "generate_and_save_resume_bullets",
    "generate_and_save_interview_story",
]

WRITE_TOOL_NAMES: frozenset[str] = frozenset(WRITE_TOOLS)

DEFAULT_ALLOWED_TOOLS: list[str] = READ_TOOLS + WRITE_TOOLS


class McpSettings(BaseSettings):
    mcp_enabled: bool = Field(default=False)
    mcp_api_base_url: str = Field(default="http://127.0.0.1:8000")
    mcp_internal_token: str = Field(default="")
    mcp_allowed_tools: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS))
    mcp_allow_write_tools: bool = Field(default=False)
    mcp_allow_file_access: bool = Field(default=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = McpSettings()
