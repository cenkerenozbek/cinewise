"""NLP batch pipeline for content-based movie recommendations.

Reads movie documents from MongoDB, preprocesses text fields, computes TF-IDF
vectors, builds a precomputed top-50 cosine similarity index, and persists
artifacts to disk for fast startup by the recommendation API.

Usage:
    python jobs/nlp_features.py
"""

import asyncio
import html
import logging
import os
import re
import sys

import joblib
import numpy as np
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path so shared/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def preprocess_text(
    overview: str | None,
    genres: list[str],
    cast: list[str] | None = None,
    director: str | None = None,
) -> str:
    """Build composite text from movie overview, genres, cast, and director.

    Cast and director are weighted by repetition (×2) so they exert stronger
    influence on TF-IDF similarity than passing mention in the overview.

    Args:
        overview: Movie overview text, may be None.
        genres: List of genre name strings.
        cast: Optional list of cast member names.
        director: Optional director name.

    Returns:
        Cleaned composite text string.
    """
    text = overview or ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = [text] if text else []
    if genres:
        parts.append(" ".join(genres))
    if cast:
        cast_str = " ".join(cast[:5])
        parts.extend([cast_str, cast_str])  # ×2 weight
    if director:
        parts.extend([director, director])  # ×2 weight
    return " ".join(parts)


def build_tfidf_matrix(texts: list[str]):
    """Fit a TF-IDF vectorizer on corpus texts and return matrix.

    Uses bigrams, English stop words, and sublinear TF scaling.
    Falls back to min_df=1 for very small corpora where min_df=2
    would result in an empty vocabulary.

    Args:
        texts: List of preprocessed text strings.

    Returns:
        Tuple of (fitted TfidfVectorizer, sparse TF-IDF matrix).
    """
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
        min_df=2,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        if tfidf_matrix.shape[1] == 0:
            raise ValueError("Empty vocabulary with min_df=2")
    except ValueError:
        # Small corpus — fall back to min_df=1
        vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
    return vectorizer, tfidf_matrix


def build_similarity_index(tfidf_matrix, top_n: int = 50) -> np.ndarray:
    """Build a precomputed top-N cosine similarity index.

    Iterates row-by-row to remain memory-safe for large corpora.
    For corpora smaller than top_n + 1, effective_top_n is capped at N-1.
    Self-similarity is excluded by setting sims[i] = -1.0 before selection.

    Args:
        tfidf_matrix: Fitted sparse TF-IDF matrix of shape (N, vocab).
        top_n: Number of nearest neighbors to store per movie.

    Returns:
        np.ndarray of shape (N, effective_top_n) with dtype int32.
    """
    N = tfidf_matrix.shape[0]
    effective_top_n = min(top_n, N - 1)
    top_indices = np.zeros((N, effective_top_n), dtype=np.int32)
    for i in range(N):
        sims = cosine_similarity(tfidf_matrix[i], tfidf_matrix).flatten()
        sims[i] = -1.0  # exclude self
        top_indices[i] = np.argpartition(sims, -effective_top_n)[-effective_top_n:]
    return top_indices


def save_artifacts(
    vectorizer,
    tmdb_ids: list[int],
    top_indices: np.ndarray,
    artifacts_dir: str,
) -> None:
    """Persist TF-IDF vectorizer and similarity index to disk via joblib.

    Args:
        vectorizer: Fitted TfidfVectorizer object.
        tmdb_ids: Ordered list of TMDB IDs corresponding to matrix rows.
        top_indices: Precomputed top-N indices array.
        artifacts_dir: Directory path to write artifacts into.
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(vectorizer, os.path.join(artifacts_dir, "tfidf_vectorizer.joblib"))
    joblib.dump(
        {"tmdb_ids": tmdb_ids, "top_indices": top_indices},
        os.path.join(artifacts_dir, "similarity_index.joblib"),
    )
    logger.info(f"Artifacts saved to {artifacts_dir}")


async def main() -> None:
    """Orchestrate full NLP batch pipeline: read -> preprocess -> vectorize -> index -> save."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    logger.info("Reading movie documents from MongoDB...")
    cursor = db.movies.find(
        {},
        {"tmdb_id": 1, "overview": 1, "genres": 1, "cast": 1, "director": 1},
    )
    docs = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(docs)} movie documents")

    texts = [
        preprocess_text(
            d.get("overview"),
            d.get("genres", []),
            d.get("cast"),
            d.get("director"),
        )
        for d in docs
    ]
    tmdb_ids = [d["tmdb_id"] for d in docs]

    logger.info("Building TF-IDF matrix...")
    vectorizer, tfidf_matrix = build_tfidf_matrix(texts)
    logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    logger.info("Building cosine similarity index...")
    top_indices = build_similarity_index(tfidf_matrix)
    logger.info(f"Similarity index shape: {top_indices.shape}")

    save_artifacts(vectorizer, tmdb_ids, top_indices, artifacts_dir)
    logger.info(f"NLP artifacts written for {len(docs)} movies")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
