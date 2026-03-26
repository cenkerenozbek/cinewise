"""Test stubs for recommendation API — Phase 2 Wave 0.

Each test is a placeholder that will be implemented alongside the
production code. Tests raise NotImplementedError (RED phase).
"""
import pytest


# --- REC-01: Top-K recommendations ---

def test_returns_top_k():
    """Recommendation service returns exactly 10 items for valid genre input."""
    raise NotImplementedError("Stub — implement in Plan 03")


# --- REC-02: Content-based with cosine similarity ---

def test_different_genres_differ():
    """Two different genre inputs produce different recommendation result sets."""
    raise NotImplementedError("Stub — implement in Plan 03")


# --- REC-05: Cold-start handling ---

def test_cold_start():
    """A user with no interaction history gets recommendations from genre preferences alone."""
    raise NotImplementedError("Stub — implement in Plan 03")


# --- NLP-04: Explanation format ---

def test_explanation_format_genres_only():
    """Explanation string is 'Recommended because you like Action and Thriller.' for genres=['Action','Thriller']."""
    raise NotImplementedError("Stub — implement in Plan 03")


def test_explanation_format_with_mood():
    """Explanation includes mood: 'Recommended because you like Action, feeling Tense.'"""
    raise NotImplementedError("Stub — implement in Plan 03")


def test_explanation_format_single_genre():
    """Explanation for single genre: 'Recommended because you like Comedy.'"""
    raise NotImplementedError("Stub — implement in Plan 03")


# --- API-02: Recommendation endpoint ---

@pytest.mark.asyncio
async def test_endpoint_200():
    """POST /api/recommendations with valid genres returns 200 and recommendations list."""
    raise NotImplementedError("Stub — implement in Plan 03")


@pytest.mark.asyncio
async def test_endpoint_422_empty_genres():
    """POST /api/recommendations with empty genres list returns 422."""
    raise NotImplementedError("Stub — implement in Plan 03")


# --- API-05: Response time ---

@pytest.mark.asyncio
async def test_response_time():
    """POST /api/recommendations responds in under 3 seconds (p95) with mock artifacts."""
    raise NotImplementedError("Stub — implement in Plan 03")
