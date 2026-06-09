"""FastAPI router for authentication endpoints.

Endpoints:
- POST /api/auth/register  — Create a new user account
- POST /api/auth/login     — Authenticate and receive a JWT access token
- GET  /api/auth/me        — Return current user ID (protected)
"""
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.models.user import TokenResponse, UserCreate, UserProfile, UserProfileUpdate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_auth_service(db=Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    body: UserCreate,
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    """Register a new user and return the created user's id and email."""
    result = await service.register(body.email, body.password, body.first_name, body.last_name)
    return UserResponse(id=result["id"], email=result["email"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Authenticate with email+password (OAuth2 form) and return a JWT token."""
    token = await service.login(form_data.username, form_data.password)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me")
async def me(user_id: str = Depends(get_current_user)) -> dict:
    """Return the authenticated user's ID. Requires a valid Bearer token."""
    return {"user_id": user_id}


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    user_id: str = Depends(get_current_user),
    service: AuthService = Depends(_get_auth_service),
) -> UserProfile:
    doc = await service._repo.find_by_id(user_id)
    return UserProfile(
        id=user_id,
        email=doc["email"],
        first_name=doc.get("first_name"),
        last_name=doc.get("last_name"),
        avatar_id=doc.get("avatar_id"),
    )


@router.patch("/profile", response_model=UserProfile)
async def update_profile(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user),
    service: AuthService = Depends(_get_auth_service),
) -> UserProfile:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        await service._repo.update_profile(user_id, fields)
    doc = await service._repo.find_by_id(user_id)
    return UserProfile(
        id=user_id,
        email=doc["email"],
        first_name=doc.get("first_name"),
        last_name=doc.get("last_name"),
        avatar_id=doc.get("avatar_id"),
    )
