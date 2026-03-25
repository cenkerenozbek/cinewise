"""Business logic for user registration and authentication."""
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository


class AuthService:
    """Handles registration and login workflows."""

    def __init__(self, db) -> None:
        self._repo = UserRepository(db)

    async def register(self, email: str, password: str) -> dict:
        """Register a new user.

        Raises:
            HTTPException 409: if the email is already registered.

        Returns:
            dict with ``id`` and ``email`` of the created user.
        """
        existing = await self._repo.find_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user_doc = {
            "email": email,
            "hashed_password": hash_password(password),
            "created_at": datetime.now(timezone.utc),
        }
        user_id = await self._repo.create(user_doc)
        return {"id": user_id, "email": email}

    async def login(self, email: str, password: str) -> str:
        """Authenticate a user and return a JWT access token.

        Raises:
            HTTPException 401: if credentials are invalid.
        """
        user = await self._repo.find_by_email(email)
        if not user or not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return create_access_token(str(user["_id"]))
