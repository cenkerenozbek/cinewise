"""Slowapi Limiter singleton.

Defined here (not in main.py) to avoid circular imports between main.py and routers.
Key function: uses JWT user_id when available, falls back to IP address.
"""
from fastapi import Request
from slowapi import Limiter


def _get_user_id_or_ip(request: Request) -> str:
    """Return a rate-limit key: 'user:<user_id>' if JWT present, else client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            from jose import jwt
            from app.core.config import settings
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_user_id_or_ip, headers_enabled=True)
