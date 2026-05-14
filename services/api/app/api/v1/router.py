from fastapi import APIRouter

from app.api.v1.assets import router as assets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chats import router as chats_router
from app.api.v1.edges import router as edges_router
from app.api.v1.health import router as health_router
from app.api.v1.objects import router as objects_router
from app.api.v1.pages import router as pages_router
from app.api.v1.search import router as search_router
from app.api.v1.sources import router as sources_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(objects_router)
api_router.include_router(pages_router)
api_router.include_router(assets_router)
api_router.include_router(sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(chats_router)
api_router.include_router(edges_router, prefix="/edges", tags=["edges"])
api_router.include_router(search_router)
