"""Concurrency smoke tests for POST /api/recommendations — Phase 3 Plan 01.

Covers:
- API-07: 10 concurrent POST /api/recommendations requests all return 200 within 3 seconds
"""
import asyncio
import time

import pytest

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# API-07: Concurrency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_concurrent_requests(client_with_nlp, seed_movies):
    """10 concurrent POST /api/recommendations all return 200 within 3 seconds total."""
    # Each concurrent user gets a unique token so rate limits don't collide
    payload = {"genres": ["Action"]}

    async def make_request(user_index: int) -> int:
        token = create_access_token(f"concurrentuser{user_index}")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client_with_nlp.post(
            "/api/recommendations",
            json=payload,
            headers=headers,
        )
        return response.status_code

    start = time.time()
    statuses = await asyncio.gather(*[make_request(i) for i in range(10)])
    elapsed = time.time() - start

    assert all(s == 200 for s in statuses), f"Not all requests succeeded: {statuses}"
    assert elapsed < 3.0, f"10 concurrent requests took {elapsed:.2f}s (expected < 3s)"
