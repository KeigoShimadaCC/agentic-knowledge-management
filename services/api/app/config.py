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
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
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
    seed_demo_examples: bool = Field(
        default=False,
        description="On API startup, seed [Demo] pages/source/chat/edges for the demo user.",
    )
    demo_seed_email: str = Field(default="demo@knowledgeos.local")
    demo_seed_password: str = Field(default="demo-demo-demo")
    demo_seed_display_name: str = Field(default="Demo")
    cookie_secure: bool = Field(
        default=False,
        description="Set Secure flag on kos_session; enable when serving the API over HTTPS.",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
