import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://kos:kospass@localhost:5432/knowledgeos",
    )
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "+asyncpg://", "+psycopg2://"
    )


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_db_url(), pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    SessionLocal = sessionmaker(bind=get_engine())
    return SessionLocal()
