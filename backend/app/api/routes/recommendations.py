"""FastAPI router for recommendation endpoints.

Endpoints:
- POST /api/recommendations — Get personalized movie recommendations
- GET  /api/recommendations/preferences — Get saved user preferences
"""
from fastapi import APIRouter, Depends, Request, Response

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.models.recommendation import PreferenceRequest, RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _get_recommendation_service(request: Request, db=Depends(get_db)) -> RecommendationService:
    return RecommendationService(db, request.app.state)


async def _get_optional_user(request: Request) -> str | None:
    """Extract user_id from JWT if present, otherwise return None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        from jose import jwt, JWTError
        from app.core.config import settings
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


@router.post("", response_model=RecommendationResponse)
@limiter.limit("10/minute")
async def get_recommendations(
    request: Request,
    response: Response,
    body: PreferenceRequest,
    service: RecommendationService = Depends(_get_recommendation_service),
    user_id: str | None = Depends(_get_optional_user),
) -> RecommendationResponse:
    """Return top-10 personalized movie recommendations based on genre + mood preferences.

    Accepts optional Bearer token — if authenticated, saves preferences to user profile.
    Works for unauthenticated users too (cold-start, no preference persistence).
    """
    return await service.get_recommendations(body.genres, body.mood, user_id)


@router.get("/preferences")
async def get_preferences(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Return saved preferences for the authenticated user. Returns empty if none saved."""
    from app.repositories.user_preferences_repo import UserPreferencesRepository
    repo = UserPreferencesRepository(db)
    prefs = await repo.get_by_user_id(user_id)
    if prefs is None:
        return {"genres": [], "mood": None}
    return {"genres": prefs.get("genres", []), "mood": prefs.get("mood")}


@router.post("/preferences")
async def save_preferences(
    body: PreferenceRequest,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Persist recommendation preferences without requiring a recommendation refresh."""
    from app.repositories.user_preferences_repo import UserPreferencesRepository
    repo = UserPreferencesRepository(db)
    await repo.upsert(user_id, body.genres, body.mood)
    return {"genres": body.genres, "mood": body.mood}
