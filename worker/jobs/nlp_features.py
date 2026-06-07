"""NLP batch pipeline for content-based movie recommendations.

Replaces TF-IDF with sentence-transformers (all-MiniLM-L6-v2) to produce
dense 384-dim semantic embeddings per movie. Cosine similarity is computed
on L2-normalised embeddings so a simple dot product suffices.

Both neighbour indices AND actual cosine scores are saved so that the
recommendation engine can use weighted aggregation instead of raw frequency
counts, improving recommendation quality significantly.

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def preprocess_text(
    overview: str | None,
    genres: list[str],
    cast: list[str] | None = None,
    director: str | None = None,
) -> str:
    """Build composite text from movie overview, genres, cast, and director.

    Cast and director are repeated twice (×2 weight) so they exert stronger
    influence on the semantic embedding than the overview alone.
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


def build_semantic_embeddings(texts: list[str]) -> np.ndarray:
    """Encode movie texts using sentence-transformers all-MiniLM-L6-v2.

    Returns L2-normalised float32 embeddings of shape (N, 384).
    Normalisation means cosine similarity == dot product at inference time.
    """
    from sentence_transformers import SentenceTransformer  # lazy import

    logger.info("Loading sentence-transformers model all-MiniLM-L6-v2 ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info(f"Encoding {len(texts)} movie texts (batch_size=64) ...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def build_similarity_index(
    embeddings: np.ndarray,
    top_n: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Build top-N cosine similarity index from L2-normalised embeddings.

    Cosine similarity on normalised vectors equals the dot product, so we
    compute embeddings @ embeddings[i] row-by-row for memory safety.
    Self-similarity is excluded by setting sims[i] = -1.0 before argpartition.

    Args:
        embeddings: L2-normalised float32 array of shape (N, D).
        top_n: Number of nearest neighbours to keep per movie.

    Returns:
        top_indices: int32 array of shape (N, effective_top_n).
        top_scores:  float32 array of shape (N, effective_top_n) — cosine
                     similarity values stored at the same positions as indices.
    """
    N = embeddings.shape[0]
    effective_top_n = min(top_n, N - 1)
    top_indices = np.zeros((N, effective_top_n), dtype=np.int32)
    top_scores = np.zeros((N, effective_top_n), dtype=np.float32)

    for i in range(N):
        sims = (embeddings @ embeddings[i]).astype(np.float64)
        sims[i] = -2.0  # below min valid cosine (-1.0) so self is never selected
        idx = np.argpartition(sims, -effective_top_n)[-effective_top_n:]
        top_indices[i] = idx.astype(np.int32)
        top_scores[i] = sims[idx].astype(np.float32)

        if (i + 1) % 500 == 0:
            logger.info(f"Similarity index: {i + 1}/{N} rows computed")

    return top_indices, top_scores


def save_artifacts(
    tmdb_ids: list[int],
    embeddings: np.ndarray,
    top_indices: np.ndarray,
    top_scores: np.ndarray,
    artifacts_dir: str,
) -> None:
    """Persist semantic embeddings and similarity index to disk."""
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(
        {
            "tmdb_ids": tmdb_ids,
            "embeddings": embeddings.astype(np.float32),
            "top_indices": top_indices,
            "top_scores": top_scores,
        },
        os.path.join(artifacts_dir, "similarity_index.joblib"),
    )
    logger.info(f"Artifacts saved to {artifacts_dir}/similarity_index.joblib")


async def main() -> None:
    """Orchestrate full NLP batch pipeline: read → embed → index → save."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")

    from pymongo import AsyncMongoClient  # lazy import — keeps unit tests free of pymongo dep

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    logger.info("Reading movie documents from MongoDB ...")
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

    embeddings = build_semantic_embeddings(texts)
    logger.info(f"Embeddings shape: {embeddings.shape}")

    logger.info("Building cosine similarity index (top_n=100) ...")
    top_indices, top_scores = build_similarity_index(embeddings, top_n=100)
    logger.info(f"Similarity index shape: {top_indices.shape}")

    save_artifacts(tmdb_ids, embeddings, top_indices, top_scores, artifacts_dir)
    logger.info(f"NLP pipeline complete for {len(docs)} movies")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
