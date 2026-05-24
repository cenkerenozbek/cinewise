"""Tests for CF (collaborative filtering) batch pipeline.

Tests cover:
  CF-01: build_cf_index shape and dtype
  CF-02: build_cf_index self-exclusion
  CF-03: build_cf_index like/dislike scoring semantics
  CF-04: build_cf_index empty interactions
  CF-05: build_cf_index unknown movie_id silently skipped
  CF-06: save_cf_artifacts writes loadable cf_index.joblib (indices + scores)

build_cf_index now returns (cf_top_indices, cf_top_scores) — both arrays
of shape (N_movies, effective_top_n).
"""
import numpy as np
import pytest

from jobs.cf_features import build_cf_index, save_cf_artifacts


@pytest.fixture
def sample_interactions():
    """5 synthetic interactions across 3 movies and 2 users."""
    return [
        {"user_id": "user_1", "movie_id": 100, "action": "like"},
        {"user_id": "user_1", "movie_id": 101, "action": "like"},
        {"user_id": "user_1", "movie_id": 102, "action": "dislike"},
        {"user_id": "user_2", "movie_id": 100, "action": "like"},
        {"user_id": "user_2", "movie_id": 101, "action": "dislike"},
    ]


@pytest.fixture
def tmdb_ids():
    return [100, 101, 102]


# ---------------------------------------------------------------------------
# CF-01: build_cf_index shape
# ---------------------------------------------------------------------------


def test_build_cf_index_shape(sample_interactions, tmdb_ids):
    """build_cf_index returns (indices, scores) each of shape (3, 2) for 3 movies, top_n capped at N-1=2."""
    indices, scores = build_cf_index(sample_interactions, tmdb_ids, top_n=50)
    assert indices.shape == (3, 2), f"Expected (3, 2), got {indices.shape}"
    assert scores.shape == (3, 2), f"Expected (3, 2), got {scores.shape}"
    assert indices.dtype == np.int32
    assert scores.dtype == np.float32


# ---------------------------------------------------------------------------
# CF-02: self-exclusion
# ---------------------------------------------------------------------------


def test_build_cf_index_excludes_self(sample_interactions, tmdb_ids):
    """For each movie i, index i does NOT appear in cf_top_indices[i]."""
    indices, _ = build_cf_index(sample_interactions, tmdb_ids, top_n=50)
    for i in range(indices.shape[0]):
        assert i not in indices[i], f"Movie index {i} appears in its own CF neighbour list"


# ---------------------------------------------------------------------------
# CF-03: like/dislike scoring semantics
# ---------------------------------------------------------------------------


def test_build_cf_index_like_dislike_scores():
    """Function runs correctly and excludes self when both likes and dislikes are present."""
    interactions = [
        {"user_id": "user_A", "movie_id": 10, "action": "like"},
        {"user_id": "user_A", "movie_id": 11, "action": "like"},
        {"user_id": "user_B", "movie_id": 10, "action": "like"},
        {"user_id": "user_B", "movie_id": 12, "action": "dislike"},
        {"user_id": "user_C", "movie_id": 11, "action": "like"},
        {"user_id": "user_C", "movie_id": 12, "action": "dislike"},
    ]
    indices, scores = build_cf_index(interactions, [10, 11, 12], top_n=2)
    assert indices.shape == (3, 2)
    for i in range(3):
        assert i not in indices[i]


# ---------------------------------------------------------------------------
# CF-04: empty interactions
# ---------------------------------------------------------------------------


def test_build_cf_index_empty_interactions(tmdb_ids):
    """Empty interactions list returns (N_movies, 0) arrays without error."""
    indices, scores = build_cf_index([], tmdb_ids, top_n=50)
    assert indices.ndim == 2 and indices.shape == (len(tmdb_ids), 0)
    assert scores.ndim == 2 and scores.shape == (len(tmdb_ids), 0)


# ---------------------------------------------------------------------------
# CF-05: unknown movie_id silently skipped
# ---------------------------------------------------------------------------


def test_build_cf_index_unknown_movie_id_skipped(tmdb_ids):
    """Interactions with movie_ids not in tmdb_ids are silently skipped."""
    interactions = [
        {"user_id": "user_1", "movie_id": 100, "action": "like"},
        {"user_id": "user_1", "movie_id": 999, "action": "like"},  # unknown
        {"user_id": "user_2", "movie_id": 101, "action": "dislike"},
    ]
    indices, scores = build_cf_index(interactions, tmdb_ids, top_n=50)
    assert indices.shape[0] == len(tmdb_ids)


# ---------------------------------------------------------------------------
# CF-06: save_cf_artifacts
# ---------------------------------------------------------------------------


def test_save_cf_artifacts(sample_interactions, tmdb_ids, tmp_path):
    """save_cf_artifacts creates cf_index.joblib with tmdb_ids, indices, and scores keys."""
    import joblib

    indices, scores = build_cf_index(sample_interactions, tmdb_ids, top_n=50)
    save_cf_artifacts(tmdb_ids, indices, scores, str(tmp_path))

    artifact_path = tmp_path / "cf_index.joblib"
    assert artifact_path.exists()

    loaded = joblib.load(artifact_path)
    assert "tmdb_ids" in loaded
    assert "cf_top_indices" in loaded
    assert "cf_top_scores" in loaded
    assert loaded["tmdb_ids"] == tmdb_ids
    assert loaded["cf_top_indices"].shape == indices.shape
    assert loaded["cf_top_scores"].shape == scores.shape
