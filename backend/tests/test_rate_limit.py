"""Tests for rate limiting on POST /api/recommendations.

Covers:
- SEC-03: The (limit+1)th recommendation request within 1 minute returns 429
- 429 response includes Retry-After header

Production limit is 60/minute; tests exhaust it via 61 in-memory ASGI calls.
"""
import pytest

from app.core.security import create_access_token

_LIMIT = 60  # must match @limiter.limit("60/minute") in recommendations.py


# ---------------------------------------------------------------------------
# SEC-03: Rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_429_after_60(client_with_nlp, seed_movies):
    """First 60 POSTs return 200; the 61st returns 429."""
    token = create_access_token("ratelimituser60")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"genres": ["Action"]}

    statuses = []
    for _ in range(_LIMIT + 1):
        response = await client_with_nlp.post(
            "/api/recommendations",
            json=payload,
            headers=headers,
        )
        statuses.append(response.status_code)

    assert statuses[:_LIMIT] == [200] * _LIMIT, (
        f"Expected first {_LIMIT} to be 200, got: {statuses[:_LIMIT]}"
    )
    assert statuses[_LIMIT] == 429, f"Expected request {_LIMIT + 1} to be 429, got: {statuses[_LIMIT]}"


@pytest.mark.asyncio
async def test_rate_limit_includes_retry_after(client_with_nlp, seed_movies):
    """429 response from exceeded rate limit includes a Retry-After header."""
    token = create_access_token("retryafteruser60")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"genres": ["Action"]}

    last_response = None
    for _ in range(_LIMIT + 1):
        last_response = await client_with_nlp.post(
            "/api/recommendations",
            json=payload,
            headers=headers,
        )

    assert last_response is not None
    assert last_response.status_code == 429
    header_names_lower = {k.lower() for k in last_response.headers}
    assert "retry-after" in header_names_lower, (
        f"Expected 'retry-after' in response headers, got: {dict(last_response.headers)}"
    )
