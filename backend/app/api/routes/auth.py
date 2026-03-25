"""FastAPI router for authentication endpoints.

Endpoints:
- POST /api/auth/register  — Create a new user account
- POST /api/auth/login     — Authenticate and receive a JWT access token
- GET  /api/auth/me        — Return current user ID (protected)
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import TokenResponse, UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_auth_service(db=Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    """Register a new user and return the created user's id and email."""
    result = await service.register(body.email, body.password)
    return UserResponse(id=result["id"], email=result["email"])


@router.post("/login", response_model=TokenResponse)
async def login(
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
