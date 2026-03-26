"""Tests for recommendation API — Phase 2 Plan 03.

Covers:
- Service-level scoring logic (Tasks 1)
- Explanation formatting (Task 1)
- FastAPI endpoint (Task 2)
"""
import time
import pytest
import pytest_asyncio
import numpy as np

from app.services.recommendation_service import build_explanation, RecommendationService


# ---------------------------------------------------------------------------
# Task 1 — service / explanation tests (no HTTP client needed)
# ---------------------------------------------------------------------------

# --- NLP-04: Explanation format ---

def test_explanation_format_genres_only():
    """Explanation string is 'Recommended because you like Action and Thriller.' for genres=['Action','Thriller']."""
    result = build_explanation(["Action", "Thriller"], None)
    assert result == "Recommended because you like Action and Thriller."


def test_explanation_format_with_mood():
    """Explanation includes mood: 'Recommended because you like Action, feeling Tense.'"""
    result = build_explanation(["Action"], "Tense")
    assert result == "Recommended because you like Action, feeling Tense."


def test_explanation_format_single_genre():
    """Explanation for single genre: 'Recommended because you like Comedy.'"""
    result = build_explanation(["Comedy"], None)
    assert result == "Recommended because you like Comedy."


# --- REC-01: Top-K recommendations ---

@pytest.mark.asyncio
async def test_returns_top_k(client_with_nlp, seed_movies):
    """Recommendation service returns exactly 10 items for valid genre input."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.recommendation_service import RecommendationService

    # Use test_db from client_with_nlp (db is set on app.state)
    from app.main import app
    db = app.state.db
    state = app.state

    service = RecommendationService(db, state)
    result = await service.get_recommendations(["Action"], None, user_id=None)
    assert len(result.recommendations) == 10


# --- REC-02: Content-based with cosine similarity ---

@pytest.mark.asyncio
async def test_different_genres_differ(client_with_nlp, seed_movies):
    """Two different genre inputs produce different recommendation result sets."""
    from app.main import app
    db = app.state.db
    state = app.state

    service = RecommendationService(db, state)
    result_action = await service.get_recommendations(["Action"], None, user_id=None)
    result_romance = await service.get_recommendations(["Romance"], None, user_id=None)

    ids_action = {r.tmdb_id for r in result_action.recommendations}
    ids_romance = {r.tmdb_id for r in result_romance.recommendations}
    assert ids_action != ids_romance


# --- REC-05: Cold-start handling ---

@pytest.mark.asyncio
async def test_cold_start(client_with_nlp, seed_movies):
    """A user with no interaction history gets recommendations from genre preferences alone."""
    from app.main import app
    db = app.state.db
    state = app.state

    service = RecommendationService(db, state)
    # No user_id = cold-start, no preference persistence
    result = await service.get_recommendations(["Comedy"], None, user_id=None)
    assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# Task 2 — endpoint tests (use HTTP client)
# ---------------------------------------------------------------------------

# --- API-02: Recommendation endpoint ---

@pytest.mark.asyncio
async def test_endpoint_200(client_with_nlp, seed_movies):
    """POST /api/recommendations with valid genres returns 200 and recommendations list."""
    response = await client_with_nlp.post(
        "/api/recommendations",
        json={"genres": ["Action"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "recommendations" in body
    assert len(body["recommendations"]) > 0


@pytest.mark.asyncio
async def test_endpoint_422_empty_genres(client_with_nlp):
    """POST /api/recommendations with empty genres list returns 422."""
    response = await client_with_nlp.post(
        "/api/recommendations",
        json={"genres": []},
    )
    assert response.status_code == 422


# --- API-05: Response time ---

@pytest.mark.asyncio
async def test_response_time(client_with_nlp, seed_movies):
    """POST /api/recommendations responds in under 3 seconds (p95) with mock artifacts."""
    start = time.time()
    response = await client_with_nlp.post(
        "/api/recommendations",
        json={"genres": ["Action"]},
    )
    elapsed = time.time() - start
    assert response.status_code == 200
    assert elapsed < 3.0
