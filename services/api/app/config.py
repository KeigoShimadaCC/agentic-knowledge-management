from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://kos:kospass@localhost:5432/knowledgeos"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    library_root: Path = Path.home() / "KnowledgeOS" / "library"
    session_secret: str = Field(
        default="",
        description=(
            "Reserved for future CSRF tokens or signed URLs. Session cookies use opaque "
            "tokens stored as hashes in Postgres (`sessions` table), not this value."
        ),
    )
    debug: bool = False
    ai_provider: str = Field(
        default="openai",
        description=(
            "Active chat provider: 'openai' or 'anthropic'. The provider's API key must "
            "be set for AI features to work; otherwise endpoints return 503 ai_disabled."
        ),
    )
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2000
    embedding_provider: str = Field(
        default="openai",
        description=(
            "Active embedding provider. Currently only 'openai' is supported. "
            "Decoupled from ai_provider so chat can run on Anthropic while embeddings "
            "stay on OpenAI (Anthropic has no embeddings API)."
        ),
    )
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    qdrant_collection: str = "knowledgeos_chunks"
    allow_open_registration: bool = Field(
        default=True,
        description="When false, POST /auth/register returns 403 (closed appliance mode).",
    )
    chat_import_max_bytes: int = Field(
        default=25 * 1024 * 1024,
        description="Maximum accepted chat import payload size in bytes.",
    )
    asset_upload_max_bytes: int = Field(
        default=100 * 1024 * 1024,
        description="Maximum accepted asset upload payload size in bytes.",
    )
    seed_demo_examples: bool = Field(
        default=False,
        description="On API startup, seed [Demo] pages/source/chat/edges for the demo user.",
    )
    demo_seed_email: str = Field(default="demo@example.com")
    demo_seed_password: str = Field(default="demo-demo-demo")
    demo_seed_display_name: str = Field(default="Demo")
    cookie_secure: bool = Field(
        default=False,
        description="Set Secure flag on kos_session; enable when serving the API over HTTPS.",
    )
    mcp_internal_token: str = Field(
        default="",
        description=(
            "Shared token for local MCP service auth via X-KOS-Internal-Token header. "
            "Empty = disabled."
        ),
    )
    mcp_internal_user_id: str = Field(
        default="",
        description=(
            "Scope MCP_INTERNAL_TOKEN to a specific user UUID. "
            "Empty = legacy single-user fallback (token resolves to the first "
            "non-deleted user); set this for multi-user safety."
        ),
    )
    mcp_rate_limit_per_minute: int = Field(
        default=60,
        description="Max MCP write calls per minute per agent identity (sliding window).",
    )
    mcp_rate_limit_per_hour: int = Field(
        default=600,
        description="Max MCP write calls per hour per agent identity (sliding window).",
    )
    mcp_agent_id_header: str = Field(
        default="X-KOS-Agent-Id",
        description="Header name that agents use to identify themselves for rate limiting.",
    )
    ai_auto_process: bool = Field(
        False, description="Enqueue background AI jobs on page save and source ingest."
    )
    ai_auto_process_tasks: list[str] = Field(
        default_factory=lambda: ["summarize", "extract_claims", "suggest_links"],
        description=(
            "AI tasks to run in background. Subset of: summarize, extract_claims, suggest_links."
        ),
    )
    mcp_env_encryption_key: str = Field(
        default="",
        description=(
            "Fernet symmetric key for encrypting MCP connection env var secrets at rest. "
            "Generate with Fernet.generate_key(). "
            "Empty = MCP env var storage disabled (create returns 400)."
        ),
    )
    mcp_web_search_threshold: float = 0.45
    mcp_web_search_connection_name: str = ""
    settings_encryption_key: str = Field(
        default="",
        description="Fernet key for encrypting runtime Settings secrets at rest.",
    )
    settings_env_file_path: str = Field(
        default="",
        description="Optional host-mounted .env file path used by Settings export.",
    )

    kos_profile: str = Field(
        default="desktop",
        description=(
            "Deployment profile. 'desktop' (default) = loopback only; 'mobile' = bind "
            "0.0.0.0 for on-LAN iPhone access, also enables the LAN-allowlist middleware."
        ),
    )
    trusted_proxy_count: int = Field(
        default=0,
        description=(
            "Number of trusted reverse proxies in front of the API. When >0, the "
            "LAN-allowlist middleware uses X-Forwarded-For (counting back from the "
            "rightmost entry); when 0, X-Forwarded-For is ignored (safe default)."
        ),
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
