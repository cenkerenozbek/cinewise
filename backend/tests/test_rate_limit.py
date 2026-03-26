"""Tests for rate limiting on POST /api/recommendations — Phase 3 Plan 01.

Covers:
- SEC-03: The 11th recommendation request within 1 minute from the same user returns 429
- 429 response includes Retry-After header
"""
import pytest

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# SEC-03: Rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_429_after_10(client_with_nlp, seed_movies):
    """First 10 POST /api/recommendations return 200; the 11th returns 429."""
    token = create_access_token("ratelimituser")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"genres": ["Action"]}

    statuses = []
    for _ in range(11):
        response = await client_with_nlp.post(
            "/api/recommendations",
            json=payload,
            headers=headers,
        )
        statuses.append(response.status_code)

    # First 10 must be 200
    assert statuses[:10] == [200] * 10, f"Expected first 10 to be 200, got: {statuses[:10]}"
    # 11th must be 429
    assert statuses[10] == 429, f"Expected 11th to be 429, got: {statuses[10]}"


@pytest.mark.asyncio
async def test_rate_limit_includes_retry_after(client_with_nlp, seed_movies):
    """429 response from exceeded rate limit includes a Retry-After header."""
    token = create_access_token("retryafteruser")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"genres": ["Action"]}

    last_response = None
    for _ in range(11):
        last_response = await client_with_nlp.post(
            "/api/recommendations",
            json=payload,
            headers=headers,
        )

    assert last_response is not None
    assert last_response.status_code == 429
    # Header name is case-insensitive in HTTP
    header_names_lower = {k.lower() for k in last_response.headers}
    assert "retry-after" in header_names_lower, (
        f"Expected 'retry-after' in response headers, got: {dict(last_response.headers)}"
    )
