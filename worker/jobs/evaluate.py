"""Offline evaluation: HR@K, NDCG@K, MRR with random and popularity baselines.

History-driven evaluation: scores candidates directly from each user's
training interaction history using the NLP similarity index and CF index,
without routing through the live recommendation service.

Metrics computed
----------------
- Hit Rate @ K  (HR@K)  — fraction of test users where the held-out movie
  appears in the top-K recommendations.  Also called Recall@K when there is
  exactly one relevant item.  Previously mis-labelled as "Precision@K" in the
  codebase; the name is corrected here.
- NDCG @ K — Normalised Discounted Cumulative Gain, penalises lower ranks.
- MRR     — Mean Reciprocal Rank (rank-aware HR variant).
- HR@5 / HR@20 — same metric at two additional cut-offs.

Baselines
---------
- Random     — uniformly sample 10 movies from all catalogue items (seed 42).
- Popularity — always recommend the 10 most popular movies (by vote_count).

Usage:
    python jobs/evaluate.py [--max-users 500] [--artifacts-dir /artifacts]
                            [--history-limit 1|3|5] [--output-path path/to/metrics.json]
"""

import argparse
import asyncio
import json
import logging
import math
import os
import random
import sys
from datetime import date

import joblib
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics import ndcg_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_CF_THRESHOLD = 5
_DEFAULT_CF_ALPHA = 0.5


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


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
    """Smooth sigmoid transition from pure content (1.0) to blended (cf_alpha).

    Replaces the old step function (pure content below threshold, sudden jump
    at threshold) with a sigmoid centred at cf_threshold so that CF influence
    grows gradually as the user accumulates interactions.

    alpha = 1.0 at n=0, converges toward cf_alpha as n → ∞.
    """
    if n_interactions <= 0:
        return 1.0
    x = (n_interactions - cf_threshold) / max(cf_threshold / 2.0, 1.0)
    blend = 1.0 / (1.0 + math.exp(-x))
    return 1.0 - (1.0 - cf_alpha) * blend


def score_from_history(
    training_ids: list[int],
    nlp_data: dict,
    cf_data: dict | None,
    cf_threshold: int = _DEFAULT_CF_THRESHOLD,
    cf_alpha: float = _DEFAULT_CF_ALPHA,
) -> dict[int, float]:
    """Score candidate movies using NLP and CF indices from training history.

    Uses weighted cosine similarity scores when available (top_scores key in
    nlp_data / cf_data).  Falls back to frequency-count accumulation for
    backward-compatible loading of old artifacts that lack score arrays.

    Args:
        training_ids: TMDB IDs of liked movies in the training split.
        nlp_data: Loaded similarity_index.joblib dict.
        cf_data: Loaded cf_index.joblib dict, or None for content-only mode.

    Returns:
        Dict mapping candidate tmdb_id → blended score (higher is better).
    """
    tmdb_ids: list[int] = nlp_data["tmdb_ids"]
    top_indices = nlp_data["top_indices"]
    top_scores = nlp_data.get("top_scores")  # None for old-format artifacts
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    # Content: weighted sum of cosine similarities from NLP neighbours
    content_scores: dict[int, float] = {}
    for mid in training_ids:
        idx = id_to_idx.get(mid)
        if idx is None:
            continue
        for j, neighbor_idx in enumerate(top_indices[idx]):
            neighbor_id = tmdb_ids[int(neighbor_idx)]
            sim = float(top_scores[idx][j]) if top_scores is not None else 1.0
            content_scores[neighbor_id] = content_scores.get(neighbor_id, 0.0) + sim

    if not content_scores:
        return {}

    # CF: weighted sum of latent-factor cosine similarities
    cf_scores: dict[int, float] = {}
    if cf_data is not None:
        cf_tmdb_ids: list[int] = cf_data["tmdb_ids"]
        cf_top_indices = cf_data["cf_top_indices"]
        cf_top_scores = cf_data.get("cf_top_scores")
        cf_id_to_idx = {tid: i for i, tid in enumerate(cf_tmdb_ids)}
        for mid in training_ids:
            idx = cf_id_to_idx.get(mid)
            if idx is None:
                continue
            for j, neighbor_idx in enumerate(cf_top_indices[idx]):
                neighbor_id = cf_tmdb_ids[int(neighbor_idx)]
                if neighbor_id in content_scores:
                    sim = float(cf_top_scores[idx][j]) if cf_top_scores is not None else 1.0
                    cf_scores[neighbor_id] = cf_scores.get(neighbor_id, 0.0) + sim

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


def hit_rate_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Return 1.0 if relevant_id appears in the top-k recommended IDs, else 0.0.

    This metric is also known as Recall@K when there is exactly one relevant
    item.  It was previously mis-named precision_at_k in this codebase.

    Args:
        recommended_ids: Ordered list of recommended TMDB IDs (best first).
        relevant_id: The held-out ground-truth TMDB ID.
        k: Cut-off rank (default 10).
    """
    return 1.0 if relevant_id in recommended_ids[:k] else 0.0


# Keep legacy alias so existing imports continue to work during transition
precision_at_k = hit_rate_at_k


def compute_ndcg_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Compute NDCG@K for a single held-out relevant item.

    Builds binary relevance labels (y_true) with 1.0 at the position of the
    relevant item, then calls sklearn.metrics.ndcg_score on (1, k) arrays.

    Returns 0.0 if relevant_id is not in the top-k.
    """
    top_k = recommended_ids[:k]
    if relevant_id not in top_k:
        return 0.0
    y_true = np.zeros((1, k), dtype=np.float64)
    y_score = np.arange(k, 0, -1, dtype=np.float64).reshape(1, k)
    y_true[0, top_k.index(relevant_id)] = 1.0
    return float(ndcg_score(y_true, y_score, k=k))


def compute_mrr(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Compute Mean Reciprocal Rank contribution for a single query.

    Returns 1 / rank if relevant_id is found within top-k, else 0.0.
    Rank is 1-indexed.
    """
    top_k = recommended_ids[:k]
    if relevant_id not in top_k:
        return 0.0
    return 1.0 / (top_k.index(relevant_id) + 1)


def build_leave_one_out_test_set(
    interactions: list[dict],
    min_likes: int = 5,
    max_users: int = 500,
) -> list[tuple[str, int, list[int]]]:
    """Build a leave-one-out evaluation test set from interaction documents.

    Groups by user, keeps only 'like' actions, excludes users with fewer than
    min_likes, sorts each user's history by updated_at ascending, holds out
    the most recent like as ground truth.

    Returns:
        List of (user_id, held_out_movie_id, training_movie_ids) tuples.
    """
    user_likes: dict[str, list[dict]] = {}
    for doc in interactions:
        if doc.get("action") != "like":
            continue
        uid = doc["user_id"]
        user_likes.setdefault(uid, []).append(doc)

    test_set: list[tuple[str, int, list[int]]] = []
    for uid, likes in user_likes.items():
        if len(likes) < min_likes:
            continue
        sorted_likes = sorted(
            likes,
            key=lambda d: d.get("updated_at") or (d["_id"].generation_time if "_id" in d else 0),
        )
        held_out_doc = sorted_likes[-1]
        training_docs = sorted_likes[:-1]
        test_set.append((uid, held_out_doc["movie_id"], [d["movie_id"] for d in training_docs]))

    random.Random(42).shuffle(test_set)
    return test_set[:max_users]


# ---------------------------------------------------------------------------
# Main evaluation orchestration
# ---------------------------------------------------------------------------


async def main() -> None:
    """Load artifacts → query DB → compute metrics + baselines → write JSON."""
    parser = argparse.ArgumentParser(description="Offline evaluation: HR@K, NDCG@K, MRR")
    parser.add_argument("--max-users", type=int, default=500)
    parser.add_argument("--min-likes", type=int, default=3, help="Minimum likes per user to qualify for evaluation (default: 3).")
    parser.add_argument("--artifacts-dir", type=str, default=None)
    parser.add_argument(
        "--history-limit",
        type=int,
        default=None,
        help="Limit training history to last N interactions (cold-start simulation).",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Custom output path for metrics JSON (default: <artifacts-dir>/metrics.json).",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = args.artifacts_dir or os.environ.get("ARTIFACTS_DIR", "/artifacts")
    cf_threshold = int(os.environ.get("CF_THRESHOLD", str(_DEFAULT_CF_THRESHOLD)))
    cf_alpha = float(os.environ.get("CF_ALPHA", str(_DEFAULT_CF_ALPHA)))

    from pymongo import AsyncMongoClient  # lazy import — keeps unit tests free of pymongo dep

    logger.info(f"Connecting to MongoDB at {mongo_uri}, db={db_name}")
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Load NLP artifact (required)
    nlp_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    logger.info(f"Loading NLP artifact from {nlp_path}")
    nlp_data = joblib.load(nlp_path)
    all_nlp_ids: set[int] = set(nlp_data["tmdb_ids"])

    # Load CF artifact (optional)
    cf_path = os.path.join(artifacts_dir, "cf_index.joblib")
    cf_data: dict | None = None
    if os.path.exists(cf_path):
        logger.info(f"Loading CF artifact from {cf_path}")
        cf_data = joblib.load(cf_path)
    else:
        logger.info("CF artifact not found — running pure content-based evaluation")

    # Fetch popularity ranking (top-200 by vote_count, fallback to rating)
    logger.info("Fetching popularity baseline (top-200 movies) ...")
    pop_cursor = db.movies.find({}).sort([("vote_count", -1), ("rating", -1)]).limit(200)
    popular_docs = await pop_cursor.to_list(length=None)
    popularity_ids: list[int] = [d["tmdb_id"] for d in popular_docs]

    # Query seed_user interactions
    logger.info("Querying seed_user_* interactions from MongoDB ...")
    cursor = db.interactions.find({"user_id": {"$regex": "^seed_user_"}})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} seed_user interactions")

    test_set = build_leave_one_out_test_set(interactions, min_likes=args.min_likes, max_users=args.max_users)
    logger.info(f"Built test set with {len(test_set)} qualifying users (min_likes={args.min_likes})")
    if args.history_limit:
        logger.info(f"History limit: {args.history_limit} interactions per user")

    if not test_set:
        logger.warning(f"No qualifying users found — check seed interactions (need >={args.min_likes} likes each)")
        await client.aclose()
        return

    # Metric accumulators
    hr10_scores: list[float] = []
    hr5_scores: list[float] = []
    hr20_scores: list[float] = []
    ndcg_scores: list[float] = []
    mrr_scores: list[float] = []
    random_hr10: list[float] = []
    pop_hr10: list[float] = []

    rng = random.Random(42)

    for i, (user_id, held_out_id, training_ids) in enumerate(test_set):
        eval_training = training_ids[-args.history_limit:] if args.history_limit else training_ids
        if not eval_training:
            continue

        candidate_scores = score_from_history(eval_training, nlp_data, cf_data, cf_threshold, cf_alpha)
        if not candidate_scores:
            logger.debug(f"User {user_id}: no candidates — skipping")
            continue

        # Remove training movies from candidate pool
        for mid in set(training_ids):
            candidate_scores.pop(mid, None)

        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)

        hr10_scores.append(hit_rate_at_k(top_ids, held_out_id, k=10))
        hr5_scores.append(hit_rate_at_k(top_ids, held_out_id, k=5))
        hr20_scores.append(hit_rate_at_k(top_ids, held_out_id, k=20))
        ndcg_scores.append(compute_ndcg_at_k(top_ids, held_out_id, k=10))
        mrr_scores.append(compute_mrr(top_ids, held_out_id, k=10))

        # Random baseline: sample 10 uniformly from NLP catalogue (excl. training)
        training_set = set(training_ids)
        random_pool = list(all_nlp_ids - training_set)
        if len(random_pool) >= 10:
            random_top10 = rng.sample(random_pool, 10)
        else:
            random_top10 = random_pool
        random_hr10.append(1.0 if held_out_id in random_top10 else 0.0)

        # Popularity baseline: top-10 most popular, excluding training movies
        pop_top10 = [tid for tid in popularity_ids if tid not in training_set][:10]
        pop_hr10.append(1.0 if held_out_id in pop_top10 else 0.0)

        if (i + 1) % 50 == 0:
            logger.info(
                f"Progress: {i+1}/{len(test_set)} — "
                f"HR@10={sum(hr10_scores)/len(hr10_scores):.4f} "
                f"NDCG@10={sum(ndcg_scores)/len(ndcg_scores):.4f} "
                f"MRR={sum(mrr_scores)/len(mrr_scores):.4f}"
            )

    if not hr10_scores:
        logger.warning("No evaluation scores computed — all test cases skipped")
        await client.aclose()
        return

    n_users = len(hr10_scores)

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 6) if lst else 0.0

    avg_hr10 = _avg(hr10_scores)
    avg_random_hr10 = _avg(random_hr10)

    # Safe improvement ratio (avoid division by zero if random baseline is 0)
    if avg_random_hr10 > 0:
        improvement_x = round(avg_hr10 / avg_random_hr10, 1)
    else:
        catalogue_size = len(all_nlp_ids)
        improvement_x = round(avg_hr10 / (10.0 / max(catalogue_size, 1)), 1)

    metrics = {
        "hit_rate_at_10": avg_hr10,
        "hit_rate_at_5": _avg(hr5_scores),
        "hit_rate_at_20": _avg(hr20_scores),
        "ndcg_at_10": _avg(ndcg_scores),
        "mrr": _avg(mrr_scores),
        "baselines": {
            "random_hit_rate_at_10": avg_random_hr10,
            "popularity_hit_rate_at_10": _avg(pop_hr10),
        },
        "improvement_vs_random_x": improvement_x,
        "eval_date": date.today().isoformat(),
        "n_users": n_users,
        "history_limit": args.history_limit,
    }

    output_path = args.output_path or os.path.join(artifacts_dir, "metrics.json")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        f"\n=== Evaluation Results ===\n"
        f"Users evaluated     : {n_users}\n"
        f"Hit Rate @ 5        : {metrics['hit_rate_at_5']:.4f}\n"
        f"Hit Rate @ 10       : {avg_hr10:.4f}\n"
        f"Hit Rate @ 20       : {metrics['hit_rate_at_20']:.4f}\n"
        f"NDCG @ 10           : {metrics['ndcg_at_10']:.4f}\n"
        f"MRR                 : {metrics['mrr']:.4f}\n"
        f"Random HR@10        : {avg_random_hr10:.4f}\n"
        f"Popularity HR@10    : {metrics['baselines']['popularity_hit_rate_at_10']:.4f}\n"
        f"Improvement vs rand : {improvement_x:.1f}x\n"
        f"Written to          : {output_path}\n"
    )

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
