"""Item-based collaborative filtering batch pipeline.

Replaces the raw item-item cosine similarity approach with SVD (Singular
Value Decomposition) latent-factor similarity. SVD extracts K latent factors
from the sparse user-item interaction matrix; item similarity is then computed
in this lower-dimensional space, which handles data sparsity far better than
direct cosine similarity on binary interactions.

Both neighbour indices AND cosine scores in latent space are saved so that
the recommendation engine can use weighted accumulation.

Falls back to normalised item-item cosine on the raw matrix when there are
too few users to run SVD (k >= min(N_users, N_movies)).

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
from scipy.sparse.linalg import svds

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_N_FACTORS = 50  # SVD latent dimensions


def build_cf_index(
    interactions: list[dict],
    tmdb_ids: list[int],
    top_n: int = 50,
    n_factors: int = _N_FACTORS,
) -> tuple[np.ndarray, np.ndarray]:
    """Build top-N item-item CF index using SVD latent factors.

    Constructs a sparse user-item matrix (like=+1, dislike=-1), decomposes it
    with truncated SVD, and computes cosine similarity on the resulting item
    latent-factor matrix.  Both neighbour indices and similarity scores are
    returned.

    Falls back to normalised item-item cosine on the raw matrix when the
    available rank is too small for the requested n_factors.

    Args:
        interactions: Interaction dicts with keys user_id, movie_id, action.
        tmdb_ids: Ordered list of canonical TMDB IDs (defines the item axis).
        top_n: Maximum CF neighbours to store per movie.
        n_factors: Number of SVD latent factors (truncated SVD rank).

    Returns:
        cf_top_indices: int32 array of shape (N_movies, effective_top_n).
        cf_top_scores:  float32 array of shape (N_movies, effective_top_n).
    """
    N_movies = len(tmdb_ids)
    tmdb_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}
    effective_top_n = min(top_n, N_movies - 1)

    empty = np.zeros((N_movies, 0), dtype=np.int32)
    empty_s = np.zeros((N_movies, 0), dtype=np.float32)
    if effective_top_n <= 0 or not interactions:
        return empty, empty_s

    # Build user and movie index mappings
    user_to_idx: dict[str, int] = {}
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for doc in interactions:
        movie_id = doc["movie_id"]
        if movie_id not in tmdb_to_idx:
            continue
        action = doc.get("action", "")
        score = 1.0 if action == "like" else (-1.0 if action == "dislike" else 0.0)
        if score == 0.0:
            continue
        uid = doc["user_id"]
        if uid not in user_to_idx:
            user_to_idx[uid] = len(user_to_idx)
        rows.append(user_to_idx[uid])
        cols.append(tmdb_to_idx[movie_id])
        data.append(score)

    if not data:
        return empty, empty_s

    N_users = len(user_to_idx)
    user_item = csr_matrix(
        (data, (rows, cols)),
        shape=(N_users, N_movies),
        dtype=np.float32,
    )

    # --- SVD or fallback ---
    effective_factors = min(n_factors, min(N_users, N_movies) - 1)

    if effective_factors >= 1:
        logger.info(f"Running SVD with k={effective_factors} latent factors ...")
        # scipy svds returns smallest singular values first; use float64 for stability
        U, sigma, Vt = svds(user_item.astype(np.float64), k=effective_factors)
        # Item latent factors weighted by singular values: (N_movies, k)
        item_factors = (Vt.T * sigma).astype(np.float32)
    else:
        logger.info("Insufficient users for SVD — using raw item-item cosine fallback")
        item_factors = user_item.T.toarray().astype(np.float32)

    # L2-normalise so dot product == cosine similarity
    norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    item_factors_norm = item_factors / norms

    # Row-by-row cosine similarity index
    cf_top_indices = np.zeros((N_movies, effective_top_n), dtype=np.int32)
    cf_top_scores = np.zeros((N_movies, effective_top_n), dtype=np.float32)

    for i in range(N_movies):
        sims = (item_factors_norm @ item_factors_norm[i]).astype(np.float64)
        sims[i] = -2.0  # below min valid cosine (-1.0) so self is never selected
        idx = np.argpartition(sims, -effective_top_n)[-effective_top_n:]
        cf_top_indices[i] = idx.astype(np.int32)
        cf_top_scores[i] = sims[idx].astype(np.float32)

        if (i + 1) % 500 == 0:
            logger.info(f"CF index: {i + 1}/{N_movies} rows computed")

    return cf_top_indices, cf_top_scores


def save_cf_artifacts(
    tmdb_ids: list[int],
    cf_top_indices: np.ndarray,
    cf_top_scores: np.ndarray,
    artifacts_dir: str,
) -> None:
    """Persist CF index (indices + scores) to disk via joblib."""
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib.dump(
        {
            "tmdb_ids": tmdb_ids,
            "cf_top_indices": cf_top_indices,
            "cf_top_scores": cf_top_scores,
        },
        os.path.join(artifacts_dir, "cf_index.joblib"),
    )
    logger.info(f"CF artifact saved to {artifacts_dir}/cf_index.joblib")


async def main() -> None:
    """Orchestrate full CF batch pipeline: read interactions → SVD → index → save."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")

    from pymongo import AsyncMongoClient  # lazy import — keeps unit tests free of pymongo dep

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    logger.info("Loading NLP artifact for canonical tmdb_ids list ...")
    sim_data = joblib.load(os.path.join(artifacts_dir, "similarity_index.joblib"))
    tmdb_ids = sim_data["tmdb_ids"]
    logger.info(f"Loaded {len(tmdb_ids)} canonical tmdb_ids")

    logger.info("Reading interactions from MongoDB ...")
    cursor = db.interactions.find({})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} interaction documents")

    logger.info("Building CF index (SVD + cosine) ...")
    cf_top_indices, cf_top_scores = build_cf_index(interactions, tmdb_ids)
    logger.info(f"CF index shape: {cf_top_indices.shape}")

    save_cf_artifacts(tmdb_ids, cf_top_indices, cf_top_scores, artifacts_dir)
    logger.info(f"CF pipeline complete for {len(tmdb_ids)} movies")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
