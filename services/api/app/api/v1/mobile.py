from fastapi import APIRouter, Depends

from app.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import MobileBootstrapResponse, MobileCapabilities, UserOut
from app.search.embedding import get_embedding_provider

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/bootstrap", response_model=MobileBootstrapResponse)
async def bootstrap(user: User = Depends(get_current_user)) -> MobileBootstrapResponse:
    return MobileBootstrapResponse(
        user=UserOut.model_validate(user),
        capabilities=MobileCapabilities(
            ai_enabled=bool(settings.openai_api_key),
            embeddings_enabled=get_embedding_provider().is_enabled,
            upload_enabled=True,
            mobile_api_version=1,
        ),
    )
