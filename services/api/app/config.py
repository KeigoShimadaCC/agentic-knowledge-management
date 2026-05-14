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
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    qdrant_collection: str = "knowledgeos_chunks"
    allow_open_registration: bool = Field(
        default=True,
        description="When false, POST /auth/register returns 403 (closed appliance mode).",
    )
    cookie_secure: bool = Field(
        default=False,
        description="Set Secure flag on kos_session; enable when serving the API over HTTPS.",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
