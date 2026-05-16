from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.library import ensure_library_structure


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    from app.db.session import AsyncSessionLocal
    from app.search import qdrant_client as qc
    from app.services import demo_seed_service, reindex_service

    log = logging.getLogger(__name__)
    ensure_library_structure()
    await qc.create_collection_if_not_exists()

    async with AsyncSessionLocal() as db:
        try:
            await demo_seed_service.migrate_legacy_demo_email(db)
            await db.commit()
        except Exception:
            log.exception("Legacy demo email migration failed")
            await db.rollback()

    if settings.seed_demo_examples:
        async with AsyncSessionLocal() as db:
            try:
                reindex_ids = await demo_seed_service.seed_demo_examples(db)
                await db.commit()
                for oid in reindex_ids:
                    reindex_service.enqueue_reindex_object(oid)
            except Exception:
                log.exception("Demo seed failed; continuing without demo data")
                await db.rollback()

    yield


app = FastAPI(title="KnowledgeOS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # localhost vs 127.0.0.1 are different origins; compose publishes web on 127.0.0.1:3000.
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": "http_error"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


app.include_router(api_router)
