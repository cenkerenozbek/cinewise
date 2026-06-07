"""Tests for the feedback API — Phase 3 Plan 01.

Covers:
- POST /api/feedback returns 204 for authenticated users (like and dislike)
- Upsert semantics: submitting feedback for the same movie replaces previous action
- 401 returned for unauthenticated requests
- 422 returned for invalid action values
- Interaction document persisted in MongoDB interactions collection
"""
import pytest

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(user_id: str = "testuser123") -> dict:
    """Return Authorization header dict with a valid JWT for user_id."""
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# DATA-03 / API-03: Feedback endpoint behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_like_returns_204(client, seed_movies):
    """POST /api/feedback with valid JWT and action='like' returns 204."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like"},
        headers=_auth_headers(),
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_submit_dislike_returns_204(client, seed_movies):
    """POST /api/feedback with valid JWT and action='dislike' returns 204."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "dislike"},
        headers=_auth_headers(),
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_upsert_replaces_action(client, test_db, seed_movies):
    """Submitting like then dislike for same movie results in a single doc with action='dislike'."""
    headers = _auth_headers("upsertuser")

    # First: like
    r1 = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like"},
        headers=headers,
    )
    assert r1.status_code == 204

    # Second: dislike (same movie_id, same user)
    r2 = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "dislike"},
        headers=headers,
    )
    assert r2.status_code == 204

    # Only one document should exist; action must be "dislike"
    count = await test_db.interactions.count_documents({"user_id": "upsertuser", "movie_id": 100})
    assert count == 1

    doc = await test_db.interactions.find_one({"user_id": "upsertuser", "movie_id": 100})
    assert doc is not None
    assert doc["action"] == "dislike"


@pytest.mark.asyncio
async def test_401_without_jwt(client):
    """POST /api/feedback without Authorization header returns 401."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_422_invalid_action(client):
    """POST /api/feedback with action='neutral' returns 422."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "neutral"},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_interaction_persisted_in_db(client, test_db, seed_movies):
    """After POSTing like, the interaction document is stored in the interactions collection."""
    headers = _auth_headers("persistuser")

    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like"},
        headers=headers,
    )
    assert response.status_code == 204

    doc = await test_db.interactions.find_one({"user_id": "persistuser", "movie_id": 100})
    assert doc is not None
    assert doc["action"] == "like"
    assert doc["movie_id"] == 100
    assert doc["user_id"] == "persistuser"


# ---------------------------------------------------------------------------
# Watch completion tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_feedback_with_watch_completion(client, test_db, seed_movies):
    """POST /api/feedback with watch_completion=0.85 returns 204 and stores the value."""
    headers = _auth_headers("watchuser")

    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like", "watch_completion": 0.85},
        headers=headers,
    )
    assert response.status_code == 204

    doc = await test_db.interactions.find_one({"user_id": "watchuser", "movie_id": 100})
    assert doc is not None
    assert doc["watch_completion"] == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_submit_feedback_completion_out_of_range(client):
    """POST /api/feedback with watch_completion=1.5 returns 422."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "like", "watch_completion": 1.5},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_watch_completion_optional(client, seed_movies):
    """POST /api/feedback without watch_completion field still returns 204 (backward compat)."""
    response = await client.post(
        "/api/feedback",
        json={"movie_id": 100, "action": "dislike"},
        headers=_auth_headers(),
    )
    assert response.status_code == 204
