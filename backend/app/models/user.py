"""Pydantic models for user-related API request/response bodies."""
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for POST /api/auth/register."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response body after successful registration."""

    id: str
    email: str


class TokenResponse(BaseModel):
    """Response body after successful login."""

    access_token: str
    token_type: str = "bearer"
