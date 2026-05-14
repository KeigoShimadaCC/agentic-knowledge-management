import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

_pool_kwargs: dict = {"poolclass": NullPool} if os.environ.get("TEST_MODE") else {"pool_pre_ping": True}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
