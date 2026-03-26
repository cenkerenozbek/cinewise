"""Offline evaluation: Precision@10 and NDCG@10 using leave-one-out.

History-driven evaluation: scores candidates directly from each user's
training interaction history using the NLP similarity index and CF index,
without routing through the live recommendation service.

This matches the proposal's intent: measure how quickly the hybrid engine
converges to relevant recommendations given limited interaction history.

Usage:
    python jobs/evaluate.py [--max-users 500] [--artifacts-dir /artifacts]
                            [--history-limit 1|3|5]
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
from datetime import date

import joblib
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics import ndcg_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Defaults — overridden in main() after load_dotenv()
_DEFAULT_CF_THRESHOLD = 5
_DEFAULT_CF_ALPHA = 0.5


def _norm(scores: dict) -> dict:
    """Min-max normalise a score dict to [0, 1]."""
    if not scores:
        return scores
    min_s = min(scores.values())
    max_s = max(scores.values())
    if max_s == min_s:
        return {k: 0.5 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


def _get_alpha(n_interactions: int, cf_threshold: int, cf_alpha: float) -> float:
    """Return content weight alpha: 1.0 (pure content) below threshold, cf_alpha above."""
    return cf_alpha if n_interactions >= cf_threshold else 1.0


def score_from_history(
    training_ids: list[int],
    nlp_data: dict,
    cf_data: dict | None,
    cf_threshold: int = _DEFAULT_CF_THRESHOLD,
    cf_alpha: float = _DEFAULT_CF_ALPHA,
) -> dict[int, float]:
    """Score candidate movies using NLP and CF indices from training history.

    For each training movie, collects NLP neighbors (content signal) and CF
    neighbors (collaborative signal), blends them by alpha, and returns a
    {tmdb_id: score} dict.  Training movies themselves are NOT excluded here
    so that the caller can choose which items to filter.

    Args:
        training_ids: TMDB IDs of movies the user liked in training split.
        nlp_data: Loaded similarity_index.joblib dict.
        cf_data: Loaded cf_index.joblib dict, or None for content-only mode.

    Returns:
        Dict mapping candidate tmdb_id → blended score (higher is better).
    """
    tmdb_ids: list[int] = nlp_data["tmdb_ids"]
    top_indices = nlp_data["top_indices"]
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    # Content: NLP neighbors of each training movie
    content_scores: dict[int, float] = {}
    for mid in training_ids:
        idx = id_to_idx.get(mid)
        if idx is None:
            continue
        for neighbor_idx in top_indices[idx]:
            neighbor_id = tmdb_ids[int(neighbor_idx)]
            content_scores[neighbor_id] = content_scores.get(neighbor_id, 0.0) + 1.0

    if not content_scores:
        return {}

    # CF: CF neighbors of each training movie (only re-scores existing candidates)
    cf_scores: dict[int, float] = {}
    if cf_data is not None:
        cf_tmdb_ids: list[int] = cf_data["tmdb_ids"]
        cf_top_indices = cf_data["cf_top_indices"]
        cf_id_to_idx = {tid: i for i, tid in enumerate(cf_tmdb_ids)}
        for mid in training_ids:
            idx = cf_id_to_idx.get(mid)
            if idx is None:
                continue
            for neighbor_idx in cf_top_indices[idx]:
                neighbor_id = cf_tmdb_ids[int(neighbor_idx)]
                if neighbor_id in content_scores:
                    cf_scores[neighbor_id] = cf_scores.get(neighbor_id, 0.0) + 1.0

    # Blend
    alpha = _get_alpha(len(training_ids), cf_threshold, cf_alpha) if cf_data else 1.0
    if cf_scores and alpha < 1.0:
        norm_content = _norm(content_scores)
        norm_cf = _norm(cf_scores)
        return {
            tid: alpha * norm_content.get(tid, 0.0) + (1.0 - alpha) * norm_cf.get(tid, 0.0)
            for tid in content_scores
        }
    return content_scores


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
        # Sort ascending by updated_at (or _id as fallback for seeded data without timestamps)
        sorted_likes = sorted(likes, key=lambda d: d.get("updated_at") or (d["_id"].generation_time if "_id" in d else 0))
        held_out_doc = sorted_likes[-1]
        training_docs = sorted_likes[:-1]
        held_out_id = held_out_doc["movie_id"]
        training_ids = [d["movie_id"] for d in training_docs]
        test_set.append((uid, held_out_id, training_ids))

    # Deterministic shuffle before capping (seed=42 for reproducible capstone metrics)
    random.Random(42).shuffle(test_set)
    return test_set[:max_users]


# ---------------------------------------------------------------------------
# Main evaluation orchestration
# ---------------------------------------------------------------------------


async def main() -> None:
    """Orchestrate offline evaluation: load artifacts -> query DB -> compute metrics -> write JSON."""
    parser = argparse.ArgumentParser(description="Offline evaluation: Precision@10 and NDCG@10")
    parser.add_argument("--max-users", type=int, default=500, help="Max test users (default 500)")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Artifacts directory")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=None,
        help="Limit training history to last N interactions per user (e.g. 1, 3, 5). "
             "Simulates cold-start convergence as per proposal N∈{1,3,5} protocol.",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = args.artifacts_dir or os.environ.get("ARTIFACTS_DIR", "/artifacts")
    cf_threshold = int(os.environ.get("CF_THRESHOLD", str(_DEFAULT_CF_THRESHOLD)))
    cf_alpha = float(os.environ.get("CF_ALPHA", str(_DEFAULT_CF_ALPHA)))

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

    # Query seed_user interactions
    logger.info("Querying seed_user_* interactions from MongoDB...")
    cursor = db.interactions.find({"user_id": {"$regex": "^seed_user_"}})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} seed_user interactions")

    # Build leave-one-out test set
    test_set = build_leave_one_out_test_set(interactions, min_likes=5, max_users=args.max_users)
    logger.info(f"Built test set with {len(test_set)} qualifying users")
    if args.history_limit:
        logger.info(f"History limit: {args.history_limit} interactions per user (cold-start mode)")

    if not test_set:
        logger.warning("No qualifying users found — check seed interactions (need >=5 likes each)")
        await client.aclose()
        return

    precision_scores: list[float] = []
    ndcg_scores: list[float] = []

    for i, (user_id, held_out_id, training_ids) in enumerate(test_set):
        # Apply history limit: use only the last N training interactions
        eval_training = training_ids[-args.history_limit:] if args.history_limit else training_ids

        if not eval_training:
            continue

        # Score candidates directly from history (history-driven, no service call)
        candidate_scores = score_from_history(eval_training, nlp_data, cf_data, cf_threshold, cf_alpha)

        if not candidate_scores:
            logger.debug(f"User {user_id}: no candidates — skipping")
            continue

        # Exclude only training movies (seen); held-out stays in pool
        for mid in set(training_ids):
            candidate_scores.pop(mid, None)

        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)[:10]

        p = precision_at_k(top_ids, held_out_id)
        n = compute_ndcg_at_k(top_ids, held_out_id)
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
        await client.aclose()
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

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
