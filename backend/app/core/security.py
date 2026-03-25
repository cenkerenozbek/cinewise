"""
Security utilities for JWT token creation/verification and bcrypt password hashing.

Exports:
- hash_password: Create bcrypt hash from plaintext password
- verify_password: Check plaintext against bcrypt hash
- create_access_token: Create a signed JWT access token
- get_current_user: FastAPI dependency that extracts and validates a Bearer JWT
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed* bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Create and return a signed JWT access token with *subject* as the `sub` claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency: extract and validate JWT Bearer token.

    Returns the user ID (``sub`` claim) from a valid token.
    Raises HTTP 401 for any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id
