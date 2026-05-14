from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_ALLOWED_TOOLS: list[str] = [
    "search_objects",
    "hybrid_search",
    "get_object",
    "get_page",
    "get_source",
    "get_related_objects",
    "answer_from_kb",
]


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
