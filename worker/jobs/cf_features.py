"""Item-based collaborative filtering batch pipeline.

Reads user-movie interaction documents from MongoDB, builds a sparse user-item
matrix, computes item-item cosine similarity, extracts top-N CF neighbors per
movie, and persists a joblib artifact for fast API startup.

Usage:
    python jobs/cf_features.py
"""

import asyncio
import logging
import os
import sys

import joblib
import numpy as np
from dotenv import load_dotenv
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path so shared/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_cf_index(
    interactions: list[dict],
    tmdb_ids: list[int],
    top_n: int = 50,
) -> np.ndarray:
    """Build a precomputed top-N item-item collaborative filtering index.

    Constructs a sparse user-item matrix from interaction data, transposes to
    get an item-feature matrix, and computes row-by-row cosine similarity to
    identify the top-N most similar items per movie.

    Like actions contribute +1.0, dislike actions contribute -1.0.
    Interactions for movie_ids not present in tmdb_ids are silently skipped.
    Self-similarity is excluded by setting sims[i] = -1.0 before selection.

    Args:
        interactions: List of interaction dicts with keys user_id, movie_id, action.
        tmdb_ids: Ordered list of canonical TMDB IDs (defines the item axis).
        top_n: Maximum number of CF neighbors to store per movie.

    Returns:
        np.ndarray of shape (N_movies, effective_top_n) with dtype int32.
        effective_top_n = min(top_n, N_movies - 1). Returns shape (N, 0)
        if interactions is empty or effective_top_n <= 0.
    """
    N_movies = len(tmdb_ids)
    tmdb_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    effective_top_n = min(top_n, N_movies - 1)
    if effective_top_n <= 0 or not interactions:
        return np.zeros((N_movies, 0), dtype=np.int32)

    # Build user and movie index mappings
    user_to_idx: dict[str, int] = {}
    for interaction in interactions:
        uid = interaction["user_id"]
        if uid not in user_to_idx:
            user_to_idx[uid] = len(user_to_idx)

    N_users = len(user_to_idx)

    # Accumulate sparse matrix entries
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for interaction in interactions:
        movie_id = interaction["movie_id"]
        if movie_id not in tmdb_to_idx:
            continue  # silently skip unknown movies
        action = interaction.get("action", "")
        score = 1.0 if action == "like" else (-1.0 if action == "dislike" else 0.0)
        if score == 0.0:
            continue

        u_idx = user_to_idx[interaction["user_id"]]
        m_idx = tmdb_to_idx[movie_id]
        rows.append(u_idx)
        cols.append(m_idx)
        data.append(score)

    if not data:
        # All interactions were filtered out (unknown IDs or neutral actions)
        return np.zeros((N_movies, 0), dtype=np.int32)

    # Build sparse user-item CSR matrix (N_users x N_movies)
    user_item = csr_matrix(
        (data, (rows, cols)),
        shape=(N_users, N_movies),
        dtype=np.float32,
    )

    # Transpose to get item-feature matrix (N_movies x N_users)
    item_matrix = user_item.T

    # Row-by-row cosine similarity (memory-safe for large corpora)
    cf_top_indices = np.zeros((N_movies, effective_top_n), dtype=np.int32)
    for i in range(N_movies):
        sims = cosine_similarity(item_matrix[i], item_matrix).flatten()
        sims[i] = -1.0  # exclude self
        cf_top_indices[i] = np.argpartition(sims, -effective_top_n)[-effective_top_n:]

    return cf_top_indices


def save_cf_artifacts(
    tmdb_ids: list[int],
    cf_top_indices: np.ndarray,
    artifacts_dir: str,
) -> None:
    """Persist CF index to disk via joblib.

    Args:
        tmdb_ids: Ordered list of TMDB IDs corresponding to matrix rows.
        cf_top_indices: Precomputed top-N CF neighbor indices array.
        artifacts_dir: Directory path to write the artifact into.
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(
        {"tmdb_ids": tmdb_ids, "cf_top_indices": cf_top_indices},
        os.path.join(artifacts_dir, "cf_index.joblib"),
    )
    logger.info(f"CF artifact saved to {artifacts_dir}/cf_index.joblib")


async def main() -> None:
    """Orchestrate full CF batch pipeline: read interactions -> build index -> save."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Use the canonical tmdb_ids list from the NLP artifact to ensure alignment
    logger.info("Loading NLP artifact for canonical tmdb_ids list...")
    sim_data = joblib.load(os.path.join(artifacts_dir, "similarity_index.joblib"))
    tmdb_ids = sim_data["tmdb_ids"]
    logger.info(f"Loaded {len(tmdb_ids)} canonical tmdb_ids from similarity_index.joblib")

    logger.info("Reading interactions from MongoDB...")
    cursor = db.interactions.find({})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} interaction documents")

    logger.info("Building CF index...")
    cf_top_indices = build_cf_index(interactions, tmdb_ids)
    logger.info(f"CF index shape: {cf_top_indices.shape}")

    save_cf_artifacts(tmdb_ids, cf_top_indices, artifacts_dir)
    logger.info(f"CF pipeline complete for {len(tmdb_ids)} movies")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
