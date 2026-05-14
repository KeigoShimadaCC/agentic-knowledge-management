import asyncio
import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set env vars BEFORE any app imports so the engine is created with the test URL
os.environ["DATABASE_URL"] = "postgresql+asyncpg://kos:kospass@localhost:5432/knowledgeos_test"
os.environ["TEST_MODE"] = "1"  # tells session.py to use NullPool (no cross-loop connection reuse)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-tests-only")
os.environ.setdefault("LIBRARY_ROOT", "/tmp/kos-test-library")

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


def _ensure_test_db() -> None:
    """Create knowledgeos_test database if it doesn't already exist."""
    import asyncpg

    async def _run() -> None:
        conn = await asyncpg.connect("postgresql://kos:kospass@localhost:5432/postgres")
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'knowledgeos_test'"
            )
            if not exists:
                await conn.execute("CREATE DATABASE knowledgeos_test")
        finally:
            await conn.close()

    asyncio.run(_run())


_ensure_test_db()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@test.com", "password": "password123", "display_name": "Test User"},
    )
    return client
