"""Tests for recommendation API — Phase 2 Plan 03.

Covers:
- Service-level scoring logic (Tasks 1)
- Explanation formatting (Task 1)
- FastAPI endpoint (Task 2)
- Hybrid blending (Phase 3 Plan 03)
"""
import time
import pytest
import numpy as np

from app.services.recommendation_service import (
    build_explanation,
    RecommendationService,
    _apply_interaction_content_feedback,
    _apply_preference_genre_guard,
    _apply_recommendable_quality_filter,
    _norm,
    _get_alpha,
)


_GENRE_TEST_VECTORS = {
    "Action": np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
    "Adventure": np.array([0.8, 0.0, 0.0, 0.0, 0.2, 0.0], dtype=np.float32),
    "Thriller": np.array([0.5, 0.0, 0.0, 0.8, 0.0, 0.0], dtype=np.float32),
    "Crime": np.array([0.4, 0.0, 0.0, 0.8, 0.0, 0.0], dtype=np.float32),
    "Horror": np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    "Romance": np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
    "Comedy": np.array([0.0, 0.8, 0.0, 0.0, 0.0, 0.2], dtype=np.float32),
    "Drama": np.array([0.0, 0.4, 0.6, 0.0, 0.0, 0.0], dtype=np.float32),
    "Documentary": np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    "Science Fiction": np.array([0.0, 0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float32),
    "Mystery": np.array([0.0, 0.0, 0.0, 0.4, 0.8, 0.0], dtype=np.float32),
    "Animation": np.array([0.0, 0.4, 0.0, 0.0, 0.0, 1.0], dtype=np.float32),
    "Family": np.array([0.0, 0.4, 0.0, 0.0, 0.0, 0.8], dtype=np.float32),
}


def _install_genre_test_embeddings(state, docs: list[dict]) -> None:
    docs_by_id = {doc["tmdb_id"]: doc for doc in docs}
    embeddings = []
    for tmdb_id in state.tmdb_ids:
        doc = docs_by_id[tmdb_id]
        vec = np.zeros(6, dtype=np.float32)
        for genre in doc.get("genres", []):
            vec += _GENRE_TEST_VECTORS.get(genre, np.zeros(6, dtype=np.float32))
        norm = np.linalg.norm(vec)
        if norm == 0.0:
            vec[0] = 1.0
        else:
            vec /= norm
        embeddings.append(vec)
    state.movie_embeddings = np.array(embeddings, dtype=np.float32)


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


@pytest.mark.asyncio
async def test_embedding_query_tracks_updated_preferences(client_with_nlp, seed_movies):
    """Runtime preference embedding makes changed genre chips produce matching recs."""
    from app.main import app
    db = app.state.db
    state = app.state
    _install_genre_test_embeddings(state, seed_movies)

    service = RecommendationService(db, state)
    result_documentary = await service.get_recommendations(
        ["Documentary"],
        "Relaxing",
        user_id=None,
    )
    result_horror = await service.get_recommendations(["Horror"], None, user_id=None)

    documentary_ids = [r.tmdb_id for r in result_documentary.recommendations]
    horror_ids = [r.tmdb_id for r in result_horror.recommendations]

    assert "Documentary" in result_documentary.recommendations[0].genres
    assert "Horror" in result_horror.recommendations[0].genres
    assert documentary_ids != horror_ids


@pytest.mark.asyncio
async def test_history_reranks_but_does_not_override_active_genres(
    client_with_nlp,
    seed_movies,
    test_db,
):
    """Profile/history can rerank, but active genre chips constrain the result pool."""
    from app.main import app
    db = app.state.db
    state = app.state
    _install_genre_test_embeddings(state, seed_movies)

    await test_db.interactions.update_one(
        {"user_id": "genre-constraint-user", "movie_id": 107},
        {
            "$set": {
                "user_id": "genre-constraint-user",
                "movie_id": 107,
                "action": "like",
            }
        },
        upsert=True,
    )

    selected = {"Action", "Romance", "Comedy", "Drama"}
    service = RecommendationService(db, state)
    result = await service.get_recommendations(
        sorted(selected),
        None,
        user_id="genre-constraint-user",
    )

    assert len(result.recommendations) == 10
    assert all(set(item.genres) & selected for item in result.recommendations)


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


@pytest.mark.asyncio
async def test_save_preferences_endpoint(client_with_nlp, test_db):
    """POST /api/recommendations/preferences persists preferences for the logged-in user."""
    from app.core.security import create_access_token

    token = create_access_token("pref-user")
    response = await client_with_nlp.post(
        "/api/recommendations/preferences",
        json={"genres": ["Action", "Thriller"], "mood": "Tense"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"genres": ["Action", "Thriller"], "mood": "Tense"}

    saved = await test_db.user_preferences.find_one({"user_id": "pref-user"})
    assert saved is not None
    assert saved["genres"] == ["Action", "Thriller"]
    assert saved["mood"] == "Tense"


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


# ---------------------------------------------------------------------------
# REC-04: Hybrid blending — unit tests for helper functions
# ---------------------------------------------------------------------------

def test_norm_basic():
    """_norm normalizes values to [0, 1] with correct endpoints and midpoint."""
    result = _norm({"a": 1.0, "b": 3.0, "c": 5.0})
    assert result == {"a": 0.0, "b": 0.5, "c": 1.0}


def test_norm_all_equal():
    """_norm returns 0.5 for all when max == min (avoid divide-by-zero)."""
    result = _norm({"a": 2.0, "b": 2.0})
    assert result == {"a": 0.5, "b": 0.5}


def test_norm_empty():
    """_norm handles empty dict gracefully."""
    result = _norm({})
    assert result == {}


def test_alpha_zero_interactions_is_pure_content():
    """_get_alpha returns exactly 1.0 (pure content) when there are no interactions."""
    assert _get_alpha(0, 5, 0.5) == 1.0


def test_alpha_few_interactions_stays_high():
    """With only 1 interaction, alpha stays well above 0.85 (mostly content)."""
    assert _get_alpha(1, 5, 0.5) > 0.85


def test_alpha_many_interactions_converges_to_cf_alpha():
    """With many interactions (50+), alpha converges close to cf_alpha (0.5)."""
    assert _get_alpha(50, 5, 0.5) < 0.55


def test_alpha_monotonically_decreasing():
    """Alpha decreases (or stays equal) as interaction count increases."""
    alphas = [_get_alpha(n, 5, 0.5) for n in range(0, 25)]
    assert all(alphas[i] >= alphas[i + 1] for i in range(len(alphas) - 1))


def test_alpha_always_bounded():
    """Alpha is always in [cf_alpha, 1.0] regardless of interaction count."""
    for n in range(0, 30):
        a = _get_alpha(n, 5, 0.5)
        assert 0.5 <= a <= 1.0


def test_content_feedback_boosts_liked_neighbors():
    """A like immediately boosts content neighbors before CF threshold is reached."""
    scores = {200: 1.0, 201: 1.0}
    tmdb_ids = [100, 200, 201]
    top_indices = np.array([[1, 2], [0, 2], [0, 1]], dtype=np.int32)

    _apply_interaction_content_feedback(
        scores,
        liked_movie_ids=[100],
        disliked_movie_ids=[],
        tmdb_ids=tmdb_ids,
        top_indices=top_indices,
        feedback_weight=5.0,
    )

    assert scores[200] == 6.0
    assert scores[201] == 6.0


def test_content_feedback_does_not_add_unrelated_candidates():
    """Feedback reranks the current preference candidate set without expanding it."""
    scores = {200: 1.0}
    tmdb_ids = [100, 200, 201]
    top_indices = np.array([[1, 2], [0, 2], [0, 1]], dtype=np.int32)

    _apply_interaction_content_feedback(
        scores,
        liked_movie_ids=[100],
        disliked_movie_ids=[],
        tmdb_ids=tmdb_ids,
        top_indices=top_indices,
        feedback_weight=5.0,
    )

    assert scores == {200: 6.0}


def test_content_feedback_penalizes_disliked_neighbors():
    """A dislike immediately lowers content-neighbor scores."""
    scores = {200: 10.0, 201: 10.0}
    tmdb_ids = [100, 200, 201]
    top_indices = np.array([[1, 2], [0, 2], [0, 1]], dtype=np.int32)

    _apply_interaction_content_feedback(
        scores,
        liked_movie_ids=[],
        disliked_movie_ids=[100],
        tmdb_ids=tmdb_ids,
        top_indices=top_indices,
        feedback_weight=5.0,
    )

    assert scores[200] == 5.0
    assert scores[201] == 5.0


def test_preference_genre_guard_filters_when_enough_matches():
    """Cold-start ranking stays anchored to the selected genre when possible."""
    scores = {
        1: 10.0,
        2: 9.0,
        3: 8.0,
        4: 7.0,
    }
    docs = [
        {"tmdb_id": 1, "genres": ["Romance"]},
        {"tmdb_id": 2, "genres": ["Romance", "Drama"]},
        {"tmdb_id": 3, "genres": ["Romance", "Comedy"]},
        {"tmdb_id": 4, "genres": ["Action"]},
    ]

    _apply_preference_genre_guard(scores, docs, ["Romance"], top_k=3)

    assert set(scores) == {1, 2, 3}


def test_preference_genre_guard_penalizes_when_matches_are_sparse():
    """Sparse data can still return fillers, but genre matches are promoted."""
    scores = {1: 10.0, 2: 10.0}
    docs = [
        {"tmdb_id": 1, "genres": ["Romance"]},
        {"tmdb_id": 2, "genres": ["Action"]},
    ]

    _apply_preference_genre_guard(scores, docs, ["Romance"], top_k=3)

    assert scores[1] > scores[2]


def test_recommendable_quality_filter_removes_low_signal_when_enough_candidates():
    """Low-vote or zero-rating movies are removed when enough better candidates exist."""
    scores = {1: 5.0, 2: 5.0, 3: 5.0, 4: 5.0}
    docs = [
        {"tmdb_id": 1, "rating": 7.0, "vote_count": 100},
        {"tmdb_id": 2, "rating": 6.0, "vote_count": 80},
        {"tmdb_id": 3, "rating": 0.0, "vote_count": 0},
        {"tmdb_id": 4, "rating": 8.0, "vote_count": 2},
    ]

    _apply_recommendable_quality_filter(scores, docs, top_k=2)

    assert set(scores) == {1, 2}


def test_recommendable_quality_filter_removes_unsafe_titles():
    """Demo recommendations should not surface obviously mature catalog titles."""
    scores = {1: 5.0, 2: 5.0, 3: 5.0}
    docs = [
        {"tmdb_id": 1, "title": "Clean Documentary", "rating": 7.0, "vote_count": 100},
        {"tmdb_id": 2, "title": "Another Clean Film", "rating": 6.5, "vote_count": 80},
        {"tmdb_id": 3, "title": "X-Rated History", "rating": 7.5, "vote_count": 200},
    ]

    _apply_recommendable_quality_filter(scores, docs, top_k=2)

    assert set(scores) == {1, 2}


# ---------------------------------------------------------------------------
# REC-04: Hybrid blending — integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hybrid_blending_differs_from_content(client_with_hybrid, seed_movies, test_db):
    """User with >=5 interactions gets different recs than user with 0 (cold-start)."""
    from app.core.security import create_access_token
    # Seed 5 interactions for testuser
    for i in range(5):
        await test_db.interactions.update_one(
            {"user_id": "testuser", "movie_id": 100 + i},
            {"$set": {"user_id": "testuser", "movie_id": 100 + i, "action": "like"}},
            upsert=True,
        )
    token = create_access_token("testuser")
    headers = {"Authorization": f"Bearer {token}"}
    # With interactions (hybrid)
    resp_hybrid = await client_with_hybrid.post(
        "/api/recommendations", json={"genres": ["Action"]}, headers=headers
    )
    # Without interactions (pure content, no auth)
    resp_content = await client_with_hybrid.post(
        "/api/recommendations", json={"genres": ["Action"]}
    )
    assert resp_hybrid.status_code == 200
    assert resp_content.status_code == 200
    hybrid_ids = [r["tmdb_id"] for r in resp_hybrid.json()["recommendations"]]
    content_ids = [r["tmdb_id"] for r in resp_content.json()["recommendations"]]
    # At least some difference in ranking or selection
    assert hybrid_ids != content_ids


@pytest.mark.asyncio
async def test_no_cf_artifact_falls_back(client_with_nlp, seed_movies, test_db):
    """With cf_top_indices=None, user with interactions still gets valid recs (no crash)."""
    from app.main import app
    from app.core.security import create_access_token
    app.state.cf_top_indices = None
    app.state.cf_tmdb_ids = []
    for i in range(10):
        await test_db.interactions.update_one(
            {"user_id": "testuser2", "movie_id": 100 + i},
            {"$set": {"user_id": "testuser2", "movie_id": 100 + i, "action": "like"}},
            upsert=True,
        )
    token = create_access_token("testuser2")
    resp = await client_with_nlp.post(
        "/api/recommendations", json={"genres": ["Action"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) > 0


# ---------------------------------------------------------------------------
# Phase 4 Plan 01 — Cold-start edge case tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_genre_fallback_returns_results(client_with_nlp, seed_movies):
    """Genre with zero DB matches falls back to top-rated movies — non-empty result."""
    from app.main import app
    db = app.state.db
    state = app.state

    service = RecommendationService(db, state)
    # "Western" genre has no matching movies in seed_movies (100-119)
    result = await service.get_recommendations(["Western"], None, user_id=None)
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_obscure_movie_no_cf_neighbors(client_with_hybrid, seed_movies, test_db):
    """Hybrid mode returns results even when a movie's CF neighbors are all excluded seeds."""
    from app.main import app
    from app.core.security import create_access_token
    import numpy as np

    db = app.state.db
    state = app.state

    # Seed 5 interactions for testuser3 on movies 100-104 (Action genre)
    for i in range(5):
        await test_db.interactions.update_one(
            {"user_id": "testuser3", "movie_id": 100 + i},
            {"$set": {"user_id": "testuser3", "movie_id": 100 + i, "action": "like"}},
            upsert=True,
        )

    # Set CF neighbors for movies 100-104 to point only to each other (all seeds, thus excluded)
    tmdb_ids = list(state.cf_tmdb_ids)
    cf_top_indices = np.array(state.cf_top_indices, copy=True)
    for i in range(5):
        # Neighbors: only the other 4 seed movie indices (0-4)
        neighbors = [(i + j + 1) % 5 for j in range(50)]
        cf_top_indices[i] = neighbors
    state.cf_top_indices = cf_top_indices

    token = create_access_token("testuser3")
    resp = await client_with_hybrid.post(
        "/api/recommendations",
        json={"genres": ["Action"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) > 0
