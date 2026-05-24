"""Tests for NLP batch pipeline.

Tests cover:
  NLP-01: Text preprocessing (preprocess_text)
  NLP-02: Semantic similarity index (build_similarity_index)
  NLP-03: Artifact persistence (save_artifacts)

TF-IDF is replaced by sentence-transformers semantic embeddings.
build_similarity_index now takes a float32 embedding matrix and returns
(top_indices, top_scores) — both arrays of shape (N, effective_top_n).
save_artifacts no longer saves a tfidf_vectorizer; it saves top_scores instead.
"""
import numpy as np
import pytest

from jobs.nlp_features import build_similarity_index, preprocess_text, save_artifacts


# ---------------------------------------------------------------------------
# NLP-01: Text preprocessing
# ---------------------------------------------------------------------------


def test_preprocess_text_strips_html_entities():
    """preprocess_text converts '&amp;' → '&', strips <br> tags, normalises whitespace."""
    result = preprocess_text("A &amp; B <br>film", ["Drama"])
    assert result == "A & B film Drama"


def test_preprocess_text_handles_none_overview():
    """preprocess_text(None, ['Drama']) returns 'Drama' (coerces None to empty string)."""
    result = preprocess_text(None, ["Drama"])
    assert result == "Drama"


def test_preprocess_text_combines_overview_and_genres():
    result = preprocess_text("A great film", ["Action", "Thriller"])
    assert result == "A great film Action Thriller"


def test_preprocess_text_includes_cast_and_director_with_weight():
    """Cast (top 5) and director appear twice for ×2 embedding weight."""
    result = preprocess_text(
        "A film",
        ["Drama"],
        cast=["Alice", "Bob", "Carol"],
        director="David",
    )
    assert "Alice Bob Carol" in result
    assert result.count("Alice Bob Carol") == 2
    assert result.count("David") == 2


def test_preprocess_text_caps_cast_at_five():
    """Only the first 5 cast members are included."""
    result = preprocess_text("A film", ["Drama"], cast=["A", "B", "C", "D", "E", "F", "G"])
    assert "A B C D E" in result
    assert "F" not in result.split()


# ---------------------------------------------------------------------------
# NLP-02: Semantic similarity index
# ---------------------------------------------------------------------------


def _random_embeddings(n: int, dim: int = 32, seed: int = 42) -> np.ndarray:
    """Generate L2-normalised random embeddings for testing (no sentence-transformers needed)."""
    rng = np.random.default_rng(seed)
    emb = rng.standard_normal((n, dim)).astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / norms


def test_build_similarity_index_shape():
    """build_similarity_index returns (indices, scores) each of shape (N, min(top_n, N-1))."""
    embeddings = _random_embeddings(10, dim=32)
    indices, scores = build_similarity_index(embeddings, top_n=5)
    assert indices.shape == (10, 5)
    assert scores.shape == (10, 5)
    assert indices.dtype == np.int32
    assert scores.dtype == np.float32


def test_build_similarity_index_excludes_self():
    """No movie appears in its own top-N similar list."""
    embeddings = _random_embeddings(10, dim=32)
    indices, _ = build_similarity_index(embeddings, top_n=9)
    for i in range(indices.shape[0]):
        assert i not in indices[i], f"Movie {i} appears in its own similarity list"


def test_build_similarity_index_top_n_capped():
    """effective_top_n is capped at N-1 when top_n > N-1."""
    embeddings = _random_embeddings(5, dim=32)
    indices, scores = build_similarity_index(embeddings, top_n=100)
    assert indices.shape == (5, 4)  # N-1 = 4
    assert scores.shape == (5, 4)


def test_build_similarity_index_scores_are_cosine():
    """Scores are in [-1, 1] (cosine similarity range on normalised vectors)."""
    embeddings = _random_embeddings(8, dim=32)
    _, scores = build_similarity_index(embeddings, top_n=4)
    assert np.all(scores >= -1.0 - 1e-5)
    assert np.all(scores <= 1.0 + 1e-5)


# ---------------------------------------------------------------------------
# NLP-03: Artifact persistence
# ---------------------------------------------------------------------------


def test_save_artifacts(tmp_path):
    """save_artifacts creates similarity_index.joblib with tmdb_ids, top_indices, top_scores."""
    import joblib

    embeddings = _random_embeddings(6, dim=16)
    tmdb_ids = list(range(100, 106))
    indices, scores = build_similarity_index(embeddings, top_n=5)
    save_artifacts(tmdb_ids, indices, scores, str(tmp_path))

    index_path = tmp_path / "similarity_index.joblib"
    assert index_path.exists(), "similarity_index.joblib not found"

    loaded = joblib.load(index_path)
    assert "tmdb_ids" in loaded
    assert "top_indices" in loaded
    assert "top_scores" in loaded
    assert loaded["tmdb_ids"] == tmdb_ids
    assert loaded["top_indices"].shape == indices.shape
    assert loaded["top_scores"].shape == scores.shape
