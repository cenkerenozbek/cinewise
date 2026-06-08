"""Pydantic models for user-related API request/response bodies."""
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for POST /api/auth/register."""

    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None


class UserResponse(BaseModel):
    """Response body after successful registration."""

    id: str
    email: str


class UserProfile(BaseModel):
    """Response body for GET /api/auth/profile."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class UserProfileUpdate(BaseModel):
    """Request body for PATCH /api/auth/profile."""

    first_name: str | None = None
    last_name: str | None = None


class TokenResponse(BaseModel):
    """Response body after successful login."""

    access_token: str
    token_type: str = "bearer"
