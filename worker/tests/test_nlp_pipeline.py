"""Test stubs for NLP batch pipeline — Phase 2 Wave 0.

Each test is a placeholder that will be implemented alongside the
production code. Tests currently raise NotImplementedError so they
fail immediately (RED phase of TDD).
"""
import pytest


# --- NLP-01: Text preprocessing ---

def test_preprocess_text_strips_html_entities():
    """preprocess_text converts '&amp;' -> '&', strips <br> tags, normalizes whitespace."""
    raise NotImplementedError("Stub — implement in Plan 02")


def test_preprocess_text_handles_none_overview():
    """preprocess_text(None, ['Drama']) returns 'Drama' (coerces None to empty string)."""
    raise NotImplementedError("Stub — implement in Plan 02")


def test_preprocess_text_combines_overview_and_genres():
    """preprocess_text('A great film', ['Action', 'Thriller']) returns 'A great film Action Thriller'."""
    raise NotImplementedError("Stub — implement in Plan 02")


# --- NLP-02: TF-IDF vectorization ---

def test_tfidf_vectorizer_produces_sparse_matrix():
    """TfidfVectorizer.fit_transform on sample texts returns scipy sparse matrix with correct shape."""
    raise NotImplementedError("Stub — implement in Plan 02")


def test_tfidf_vectorizer_max_features():
    """Vectorizer limits vocabulary to max_features=5000."""
    raise NotImplementedError("Stub — implement in Plan 02")


# --- NLP-03: Similarity index ---

def test_similarity_index_shape():
    """Top-N similarity index has shape (N_movies, 50) with dtype int32."""
    raise NotImplementedError("Stub — implement in Plan 02")


def test_similarity_index_excludes_self():
    """No movie appears in its own top-50 similar list."""
    raise NotImplementedError("Stub — implement in Plan 02")


def test_similarity_artifacts_saved(tmp_path):
    """Artifacts tfidf_vectorizer.joblib and similarity_index.joblib are written to artifacts dir."""
    raise NotImplementedError("Stub — implement in Plan 02")
