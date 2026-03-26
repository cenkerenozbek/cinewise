"""Offline evaluation: Precision@10 and NDCG@10 using leave-one-out.

Reads seed_user interactions from MongoDB, builds a leave-one-out test set,
calls RecommendationService directly (no HTTP), computes metrics, and
writes metrics.json to the artifacts directory.

Usage:
    python jobs/evaluate.py [--max-users 500] [--artifacts-dir /artifacts]
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
from collections import Counter
from datetime import date

import joblib
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics import ndcg_score

# Add project root to path so shared/ is importable and backend/ so app/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure evaluation functions (no DB, fully unit-testable)
# ---------------------------------------------------------------------------


def precision_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Return 1.0 if relevant_id appears in the top-k recommended IDs, else 0.0.

    Args:
        recommended_ids: Ordered list of recommended TMDB IDs (best first).
        relevant_id: The held-out ground-truth TMDB ID.
        k: Cut-off rank (default 10).

    Returns:
        1.0 if relevant_id is within recommended_ids[:k], otherwise 0.0.
    """
    return 1.0 if relevant_id in recommended_ids[:k] else 0.0


def compute_ndcg_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Compute NDCG@K for a single held-out relevant item.

    Builds binary relevance labels (y_true) with 1.0 at the position of the
    relevant item and 0.0 elsewhere, and descending rank scores (y_score).
    Uses sklearn.metrics.ndcg_score on shape (1, k) arrays.

    Args:
        recommended_ids: Ordered list of recommended TMDB IDs (best first).
        relevant_id: The held-out ground-truth TMDB ID.
        k: Cut-off rank (default 10).

    Returns:
        NDCG@K score in [0.0, 1.0]. Returns 0.0 if relevant_id not in top-k.
    """
    top_k = recommended_ids[:k]
    if relevant_id not in top_k:
        return 0.0

    y_true = np.zeros((1, k), dtype=np.float64)
    y_score = np.arange(k, 0, -1, dtype=np.float64).reshape(1, k)  # [k, k-1, ..., 1]

    pos = top_k.index(relevant_id)
    y_true[0, pos] = 1.0

    return float(ndcg_score(y_true, y_score, k=k))


def build_leave_one_out_test_set(
    interactions: list[dict],
    min_likes: int = 5,
    max_users: int = 500,
) -> list[tuple[str, int, list[int]]]:
    """Build a leave-one-out evaluation test set from interaction documents.

    Groups interactions by user, filters to action=="like", excludes users
    with fewer than min_likes likes, sorts each user's likes by updated_at
    ascending, holds out the last (most recent) like as ground truth, and
    returns the remainder as the training set.

    Args:
        interactions: List of interaction dicts with keys:
            user_id (str), movie_id (int), action (str), updated_at (datetime).
        min_likes: Minimum number of likes required for a user to qualify.
        max_users: Maximum number of test cases to return (randomly sampled).

    Returns:
        List of (user_id, held_out_movie_id, training_movie_ids) tuples.
        Capped at max_users entries.
    """
    # Group likes by user
    user_likes: dict[str, list[dict]] = {}
    for doc in interactions:
        if doc.get("action") != "like":
            continue
        uid = doc["user_id"]
        if uid not in user_likes:
            user_likes[uid] = []
        user_likes[uid].append(doc)

    test_set: list[tuple[str, int, list[int]]] = []
    for uid, likes in user_likes.items():
        if len(likes) < min_likes:
            continue
        # Sort ascending by updated_at so the last element is the most recent
        sorted_likes = sorted(likes, key=lambda d: d["updated_at"])
        held_out_doc = sorted_likes[-1]
        training_docs = sorted_likes[:-1]
        held_out_id = held_out_doc["movie_id"]
        training_ids = [d["movie_id"] for d in training_docs]
        test_set.append((uid, held_out_id, training_ids))

    # Random shuffle before capping to avoid bias toward first-seen users
    random.shuffle(test_set)
    return test_set[:max_users]


# ---------------------------------------------------------------------------
# EvalState — mimics app.state for offline RecommendationService usage
# ---------------------------------------------------------------------------


class EvalState:
    """Mimics app.state attributes for offline RecommendationService usage."""

    def __init__(self, nlp_data: dict, cf_data: dict | None) -> None:
        self.tfidf_vectorizer = None
        self.tmdb_ids = nlp_data["tmdb_ids"]
        self.top_indices = nlp_data["top_indices"]
        self.cf_top_indices = cf_data["cf_top_indices"] if cf_data else None
        self.cf_tmdb_ids = cf_data["tmdb_ids"] if cf_data else []


# ---------------------------------------------------------------------------
# Main evaluation orchestration
# ---------------------------------------------------------------------------


async def main() -> None:
    """Orchestrate offline evaluation: load artifacts -> query DB -> compute metrics -> write JSON."""
    parser = argparse.ArgumentParser(description="Offline evaluation: Precision@10 and NDCG@10")
    parser.add_argument("--max-users", type=int, default=500, help="Max test users (default 500)")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Artifacts directory")
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = args.artifacts_dir or os.environ.get("ARTIFACTS_DIR", "/artifacts")

    logger.info(f"Connecting to MongoDB at {mongo_uri}, db={db_name}")
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Load NLP artifact (required)
    nlp_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    logger.info(f"Loading NLP artifact from {nlp_path}")
    nlp_data = joblib.load(nlp_path)

    # Load CF artifact (optional — falls back to pure content if missing)
    cf_path = os.path.join(artifacts_dir, "cf_index.joblib")
    cf_data: dict | None = None
    if os.path.exists(cf_path):
        logger.info(f"Loading CF artifact from {cf_path}")
        cf_data = joblib.load(cf_path)
    else:
        logger.info("CF artifact not found — running pure content-based evaluation")

    eval_state = EvalState(nlp_data, cf_data)

    # Query seed_user interactions
    logger.info("Querying seed_user_* interactions from MongoDB...")
    cursor = db.interactions.find({"user_id": {"$regex": "^seed_user_"}})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} seed_user interactions")

    # Build leave-one-out test set
    test_set = build_leave_one_out_test_set(interactions, min_likes=5, max_users=args.max_users)
    logger.info(f"Built test set with {len(test_set)} qualifying users")

    if not test_set:
        logger.warning("No qualifying users found — check seed interactions (need >=5 likes each)")
        client.close()
        return

    # Lazy import after sys.path manipulation above
    from app.services.recommendation_service import RecommendationService  # noqa: E402

    precision_scores: list[float] = []
    ndcg_scores: list[float] = []

    for i, (user_id, held_out_id, training_ids) in enumerate(test_set):
        # Derive genres from training movies: query and pick top 2 most frequent
        genre_docs = await db.movies.find(
            {"tmdb_id": {"$in": training_ids}},
            {"genres": 1},
        ).to_list(length=None)

        genre_counter: Counter = Counter()
        for gdoc in genre_docs:
            for g in gdoc.get("genres", []):
                genre_counter[g] += 1

        top_genres = [g for g, _ in genre_counter.most_common(2)]
        if not top_genres:
            logger.debug(f"User {user_id}: no genre signal — skipping")
            continue

        service = RecommendationService(db, eval_state)
        try:
            response = await service.get_recommendations(
                genres=top_genres, mood=None, user_id=user_id
            )
        except Exception as exc:
            logger.warning(f"User {user_id}: get_recommendations failed: {exc}")
            continue

        recommended_ids = [r.tmdb_id for r in response.recommendations]
        p = precision_at_k(recommended_ids, held_out_id)
        n = compute_ndcg_at_k(recommended_ids, held_out_id)
        precision_scores.append(p)
        ndcg_scores.append(n)

        if (i + 1) % 50 == 0:
            logger.info(
                f"Progress: {i+1}/{len(test_set)} users evaluated — "
                f"running P@10={sum(precision_scores)/len(precision_scores):.4f} "
                f"NDCG@10={sum(ndcg_scores)/len(ndcg_scores):.4f}"
            )

    if not precision_scores:
        logger.warning("No evaluation scores computed — all test cases skipped")
        client.close()
        return

    avg_precision = sum(precision_scores) / len(precision_scores)
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)
    n_users = len(precision_scores)

    metrics = {
        "precision_at_10": round(avg_precision, 6),
        "ndcg_at_10": round(avg_ndcg, 6),
        "eval_date": date.today().isoformat(),
        "n_users": n_users,
    }

    os.makedirs(artifacts_dir, exist_ok=True)
    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        f"\n=== Evaluation Results ===\n"
        f"Users evaluated : {n_users}\n"
        f"Precision@10    : {avg_precision:.4f}\n"
        f"NDCG@10         : {avg_ndcg:.4f}\n"
        f"Written to      : {metrics_path}\n"
    )

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
