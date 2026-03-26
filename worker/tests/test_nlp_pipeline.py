"""Tests for NLP batch pipeline — Phase 2 Plan 02.

Tests cover:
  NLP-01: Text preprocessing (preprocess_text)
  NLP-02: TF-IDF vectorization (build_tfidf_matrix)
  NLP-03: Similarity index (build_similarity_index, save_artifacts)
"""
import numpy as np
import pytest
import scipy.sparse

from jobs.nlp_features import build_tfidf_matrix, preprocess_text


# --- NLP-01: Text preprocessing ---


def test_preprocess_text_strips_html_entities():
    """preprocess_text converts '&amp;' -> '&', strips <br> tags, normalizes whitespace."""
    result = preprocess_text("A &amp; B <br>film", ["Drama"])
    assert result == "A & B film Drama"


def test_preprocess_text_handles_none_overview():
    """preprocess_text(None, ['Drama']) returns 'Drama' (coerces None to empty string)."""
    result = preprocess_text(None, ["Drama"])
    assert result == "Drama"


def test_preprocess_text_combines_overview_and_genres():
    """preprocess_text('A great film', ['Action', 'Thriller']) returns 'A great film Action Thriller'."""
    result = preprocess_text("A great film", ["Action", "Thriller"])
    assert result == "A great film Action Thriller"


# --- NLP-02: TF-IDF vectorization ---


def test_tfidf_vectorizer_produces_sparse_matrix(sample_movie_docs):
    """TfidfVectorizer.fit_transform on sample texts returns scipy sparse matrix with correct shape."""
    texts = [
        preprocess_text(doc.get("overview"), doc.get("genres", []))
        for doc in sample_movie_docs
    ]
    _vectorizer, tfidf_matrix = build_tfidf_matrix(texts)
    assert scipy.sparse.issparse(tfidf_matrix)
    assert tfidf_matrix.shape[0] == 10
    assert tfidf_matrix.shape[1] <= 5000


def test_tfidf_vectorizer_max_features(sample_movie_docs):
    """Vectorizer limits vocabulary to max_features=5000."""
    texts = [
        preprocess_text(doc.get("overview"), doc.get("genres", []))
        for doc in sample_movie_docs
    ]
    vectorizer, _matrix = build_tfidf_matrix(texts)
    assert vectorizer.max_features == 5000


# --- NLP-03: Similarity index ---


def test_similarity_index_shape(sample_movie_docs):
    """Top-N similarity index has shape (N_movies, min(50, N-1)) with dtype int32."""
    from jobs.nlp_features import build_similarity_index

    texts = [
        preprocess_text(doc.get("overview"), doc.get("genres", []))
        for doc in sample_movie_docs
    ]
    _vectorizer, tfidf_matrix = build_tfidf_matrix(texts)
    top_indices = build_similarity_index(tfidf_matrix)
    # With 10 movies, TOP_N = min(50, 10-1) = 9
    assert top_indices.shape == (10, 9)
    assert top_indices.dtype == np.int32


def test_similarity_index_excludes_self(sample_movie_docs):
    """No movie appears in its own top similar list."""
    from jobs.nlp_features import build_similarity_index

    texts = [
        preprocess_text(doc.get("overview"), doc.get("genres", []))
        for doc in sample_movie_docs
    ]
    _vectorizer, tfidf_matrix = build_tfidf_matrix(texts)
    top_indices = build_similarity_index(tfidf_matrix)
    for i in range(top_indices.shape[0]):
        assert i not in top_indices[i], f"Movie {i} appears in its own similarity list"


def test_similarity_artifacts_saved(tmp_path, sample_movie_docs):
    """Artifacts tfidf_vectorizer.joblib and similarity_index.joblib are written to artifacts dir."""
    import joblib

    from jobs.nlp_features import build_similarity_index, build_tfidf_matrix, save_artifacts

    texts = [
        preprocess_text(doc.get("overview"), doc.get("genres", []))
        for doc in sample_movie_docs
    ]
    tmdb_ids = [doc["tmdb_id"] for doc in sample_movie_docs]
    vectorizer, tfidf_matrix = build_tfidf_matrix(texts)
    top_indices = build_similarity_index(tfidf_matrix)
    save_artifacts(vectorizer, tmdb_ids, top_indices, str(tmp_path))

    vectorizer_path = tmp_path / "tfidf_vectorizer.joblib"
    index_path = tmp_path / "similarity_index.joblib"
    assert vectorizer_path.exists(), "tfidf_vectorizer.joblib not found"
    assert index_path.exists(), "similarity_index.joblib not found"

    loaded = joblib.load(index_path)
    assert "tmdb_ids" in loaded, "similarity_index.joblib missing 'tmdb_ids' key"
    assert "top_indices" in loaded, "similarity_index.joblib missing 'top_indices' key"
