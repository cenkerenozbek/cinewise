"""Offline evaluation: HR@K, NDCG@K, MRR, Genre Precision, Coverage, Novelty, ILD.

Runs a leave-one-out protocol on seed_user interactions and reports:

Accuracy metrics
----------------
- Hit Rate @ K  (HR@K)  — fraction of test users where the held-out movie
  appears in the top-K recommendations.
- NDCG @ K — Normalised Discounted Cumulative Gain, penalises lower ranks.
- MRR     — Mean Reciprocal Rank.

Beyond-accuracy metrics
-----------------------
- Genre Precision @ K — fraction of top-K recommendations that match the
  user's selected genre preferences.
- Catalog Coverage — fraction of the full catalogue that appears in at least
  one recommendation list across all evaluated users.
- Novelty — mean self-information of recommended items; higher = less popular.
- Intra-List Diversity (ILD) — average pairwise genre-Jaccard distance within
  each recommendation list; higher = more diverse.

Cold-start curve
----------------
The full evaluation is repeated at history limits [1, 3, 5, 10, None] so the
report shows how each metric evolves as users accumulate interactions.

Usage:
    python jobs/evaluate.py [--max-users 500] [--artifacts-dir /artifacts]
                            [--output-path path/to/metrics.json]
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
_COLD_START_LIMITS = [1, 3, 5, 10, None]


# ---------------------------------------------------------------------------
# Scoring helpers (unchanged)
# ---------------------------------------------------------------------------


def _norm(scores: dict) -> dict:
    if not scores:
        return scores
    min_s = min(scores.values())
    max_s = max(scores.values())
    if max_s == min_s:
        return {k: 0.5 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


def _get_alpha(n_interactions: int, cf_threshold: int, cf_alpha: float) -> float:
    if n_interactions <= 0:
        return 1.0
    x = (n_interactions - cf_threshold) / max(cf_threshold / 2.0, 1.0)
    blend = 1.0 / (1.0 + math.exp(-x))
    return 1.0 - (1.0 - cf_alpha) * blend


def _score_content_embedding(
    training_ids: list[int],
    nlp_data: dict,
) -> dict[int, float]:
    """Score all catalog movies against the mean embedding of training items.

    Removes the top-100 neighbor limit by computing similarity against the
    full catalog via a single dot-product call on L2-normalized embeddings.
    Returns an empty dict when embeddings are not available in the artifact.
    """
    embeddings = nlp_data.get("embeddings")
    if embeddings is None:
        return {}

    tmdb_ids: list[int] = nlp_data["tmdb_ids"]
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    query = np.zeros(embeddings.shape[1], dtype=np.float32)
    count = 0
    for mid in training_ids:
        idx = id_to_idx.get(mid)
        if idx is not None:
            query += embeddings[idx]
            count += 1

    if count == 0:
        return {}

    query /= count
    norm = float(np.linalg.norm(query))
    if norm == 0.0:
        return {}
    query /= norm

    sims = (embeddings @ query).astype(np.float64)
    return {tmdb_ids[i]: float(sims[i]) for i in range(len(tmdb_ids))}


def score_cf_only(
    training_ids: list[int],
    cf_data: dict,
) -> dict[int, float]:
    """Return CF-only candidate scores without any content blending."""
    cf_tmdb_ids: list[int] = cf_data["tmdb_ids"]
    cf_top_indices = cf_data["cf_top_indices"]
    cf_top_scores = cf_data.get("cf_top_scores")
    cf_id_to_idx = {tid: i for i, tid in enumerate(cf_tmdb_ids)}

    scores: dict[int, float] = {}
    for mid in training_ids:
        idx = cf_id_to_idx.get(mid)
        if idx is None:
            continue
        for j, neighbor_idx in enumerate(cf_top_indices[idx]):
            neighbor_id = cf_tmdb_ids[int(neighbor_idx)]
            sim = float(cf_top_scores[idx][j]) if cf_top_scores is not None else 1.0
            scores[neighbor_id] = scores.get(neighbor_id, 0.0) + sim
    return scores


def score_from_history(
    training_ids: list[int],
    nlp_data: dict,
    cf_data: dict | None,
    cf_threshold: int = _DEFAULT_CF_THRESHOLD,
    cf_alpha: float = _DEFAULT_CF_ALPHA,
) -> dict[int, float]:
    # Full-catalog embedding scoring removes the top-100 neighbor limit.
    # Fall back to pre-computed top_indices only for old artifacts without embeddings.
    content_scores = _score_content_embedding(training_ids, nlp_data)
    if not content_scores:
        tmdb_ids: list[int] = nlp_data["tmdb_ids"]
        top_indices = nlp_data["top_indices"]
        top_scores = nlp_data.get("top_scores")
        id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}
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
# Accuracy metrics
# ---------------------------------------------------------------------------


def hit_rate_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    return 1.0 if relevant_id in recommended_ids[:k] else 0.0


precision_at_k = hit_rate_at_k  # legacy alias


def compute_ndcg_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    top_k = recommended_ids[:k]
    if relevant_id not in top_k:
        return 0.0
    y_true = np.zeros((1, k), dtype=np.float64)
    y_score = np.arange(k, 0, -1, dtype=np.float64).reshape(1, k)
    y_true[0, top_k.index(relevant_id)] = 1.0
    return float(ndcg_score(y_true, y_score, k=k))


def compute_mrr(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    top_k = recommended_ids[:k]
    if relevant_id not in top_k:
        return 0.0
    return 1.0 / (top_k.index(relevant_id) + 1)


# ---------------------------------------------------------------------------
# Beyond-accuracy metrics
# ---------------------------------------------------------------------------


def compute_genre_precision(
    top_ids: list[int],
    user_genres: set[str],
    movie_genres: dict[int, set[str]],
    k: int = 10,
) -> float:
    """Fraction of top-K recommendations that share at least one genre with user preferences."""
    if not user_genres:
        return 0.0
    top_k = top_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(
        1 for tid in top_k
        if movie_genres.get(tid, set()) & user_genres
    )
    return hits / len(top_k)


def compute_novelty(
    top_ids: list[int],
    popularity_rank: dict[int, int],
    catalogue_size: int,
    k: int = 10,
) -> float:
    """Mean self-information of recommended items (higher = less popular = more novel).

    novelty(i) = -log2(rank_i / N)  where rank_i is 1-indexed popularity rank.
    """
    top_k = top_ids[:k]
    if not top_k:
        return 0.0
    scores = []
    for tid in top_k:
        rank = popularity_rank.get(tid, catalogue_size)
        p = rank / max(catalogue_size, 1)
        scores.append(-math.log2(max(p, 1e-10)))
    return sum(scores) / len(scores)


def compute_ild(
    top_ids: list[int],
    movie_genres: dict[int, set[str]],
    k: int = 10,
) -> float:
    """Intra-List Diversity: mean pairwise genre-Jaccard distance within top-K.

    Jaccard distance = 1 - |A∩B| / |A∪B|.  Returns 0.0 for lists with <2 items.
    """
    top_k = top_ids[:k]
    if len(top_k) < 2:
        return 0.0
    distances = []
    for i in range(len(top_k)):
        for j in range(i + 1, len(top_k)):
            a = movie_genres.get(top_k[i], set())
            b = movie_genres.get(top_k[j], set())
            union = a | b
            if not union:
                distances.append(0.0)
            else:
                distances.append(1.0 - len(a & b) / len(union))
    return sum(distances) / len(distances)


# ---------------------------------------------------------------------------
# Test-set construction
# ---------------------------------------------------------------------------


def build_leave_one_out_test_set(
    interactions: list[dict],
    min_likes: int = 5,
    max_users: int = 500,
) -> list[tuple[str, int, list[int]]]:
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
# Baseline comparison pass (full history, 4 strategies)
# ---------------------------------------------------------------------------


def run_strategy_pass(
    test_set: list[tuple[str, int, list[int]]],
    strategy: str,
    nlp_data: dict,
    cf_data: dict | None,
    cf_threshold: int,
    cf_alpha: float,
    movie_genres: dict[int, set[str]],
    user_pref_genres: dict[str, set[str]],
    popularity_rank: dict[int, int],
    all_popularity_ids: list[int],
    catalogue_size: int,
    k: int = 10,
) -> dict:
    """Evaluate a single recommendation strategy at full history.

    strategy: "popular" | "content" | "cf" | "hybrid"
    """
    hr10: list[float] = []
    ndcg10: list[float] = []
    mrr_list: list[float] = []
    gp: list[float] = []
    nov: list[float] = []
    ild_list: list[float] = []
    all_recommended: set[int] = set()

    for user_id, held_out_id, training_ids in test_set:
        if not training_ids:
            continue
        training_set = set(training_ids)

        if strategy == "popular":
            top_ids = [tid for tid in all_popularity_ids if tid not in training_set]
        elif strategy == "content":
            cands = score_from_history(training_ids, nlp_data, None, cf_threshold, cf_alpha)
            if not cands:
                continue
            for mid in training_set:
                cands.pop(mid, None)
            top_ids = sorted(cands, key=lambda x: cands[x], reverse=True)
        elif strategy == "cf":
            if cf_data is None:
                continue
            cands = score_cf_only(training_ids, cf_data)
            if not cands:
                continue
            for mid in training_set:
                cands.pop(mid, None)
            top_ids = sorted(cands, key=lambda x: cands[x], reverse=True)
        else:  # hybrid
            cands = score_from_history(training_ids, nlp_data, cf_data, cf_threshold, cf_alpha)
            if not cands:
                continue
            for mid in training_set:
                cands.pop(mid, None)
            top_ids = sorted(cands, key=lambda x: cands[x], reverse=True)

        hr10.append(hit_rate_at_k(top_ids, held_out_id, k=10))
        ndcg10.append(compute_ndcg_at_k(top_ids, held_out_id, k=10))
        mrr_list.append(compute_mrr(top_ids, held_out_id, k=10))
        all_recommended.update(top_ids[:k])

        user_genres = user_pref_genres.get(user_id, set())
        gp.append(compute_genre_precision(top_ids, user_genres, movie_genres, k))
        nov.append(compute_novelty(top_ids, popularity_rank, catalogue_size, k))
        ild_list.append(compute_ild(top_ids, movie_genres, k))

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    return {
        "strategy": strategy,
        "n_users": len(hr10),
        "precision_at_10": _avg(hr10),
        "ndcg_at_10": _avg(ndcg10),
        "mrr": _avg(mrr_list),
        "genre_precision_at_10": _avg(gp),
        "catalog_coverage": round(len(all_recommended) / max(catalogue_size, 1), 4),
        "novelty": _avg(nov),
        "intra_list_diversity": _avg(ild_list),
    }


# ---------------------------------------------------------------------------
# Single-limit evaluation pass
# ---------------------------------------------------------------------------


def run_evaluation_pass(
    test_set: list[tuple[str, int, list[int]]],
    nlp_data: dict,
    cf_data: dict | None,
    cf_threshold: int,
    cf_alpha: float,
    movie_genres: dict[int, set[str]],
    user_pref_genres: dict[str, set[str]],
    popularity_rank: dict[int, int],
    popularity_ids: list[int],
    catalogue_size: int,
    history_limit: int | None,
    k: int = 10,
) -> dict:
    all_nlp_ids: set[int] = set(nlp_data["tmdb_ids"])
    rng = random.Random(42)

    hr10_scores: list[float] = []
    hr5_scores: list[float] = []
    hr20_scores: list[float] = []
    ndcg_scores: list[float] = []
    mrr_scores: list[float] = []
    random_hr10: list[float] = []
    pop_hr10: list[float] = []
    genre_prec_scores: list[float] = []
    novelty_scores: list[float] = []
    ild_scores: list[float] = []
    all_recommended: set[int] = set()

    for user_id, held_out_id, training_ids in test_set:
        eval_training = training_ids[-history_limit:] if history_limit else training_ids
        if not eval_training:
            continue

        candidate_scores = score_from_history(
            eval_training, nlp_data, cf_data, cf_threshold, cf_alpha
        )
        if not candidate_scores:
            continue

        for mid in set(training_ids):
            candidate_scores.pop(mid, None)

        top_ids = sorted(candidate_scores, key=lambda x: candidate_scores[x], reverse=True)

        hr10_scores.append(hit_rate_at_k(top_ids, held_out_id, k=10))
        hr5_scores.append(hit_rate_at_k(top_ids, held_out_id, k=5))
        hr20_scores.append(hit_rate_at_k(top_ids, held_out_id, k=20))
        ndcg_scores.append(compute_ndcg_at_k(top_ids, held_out_id, k=10))
        mrr_scores.append(compute_mrr(top_ids, held_out_id, k=10))

        top_k = top_ids[:k]
        all_recommended.update(top_k)

        user_genres = user_pref_genres.get(user_id, set())
        genre_prec_scores.append(compute_genre_precision(top_ids, user_genres, movie_genres, k))
        novelty_scores.append(compute_novelty(top_ids, popularity_rank, catalogue_size, k))
        ild_scores.append(compute_ild(top_ids, movie_genres, k))

        training_set = set(training_ids)
        random_pool = list(all_nlp_ids - training_set)
        random_top10 = rng.sample(random_pool, 10) if len(random_pool) >= 10 else random_pool
        random_hr10.append(1.0 if held_out_id in random_top10 else 0.0)

        pop_top10 = [tid for tid in popularity_ids if tid not in training_set][:10]
        pop_hr10.append(1.0 if held_out_id in pop_top10 else 0.0)

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 6) if lst else 0.0

    n = len(hr10_scores)
    avg_hr10 = _avg(hr10_scores)
    avg_random = _avg(random_hr10)
    if avg_random > 0:
        improvement_x = round(avg_hr10 / avg_random, 1)
    else:
        improvement_x = round(avg_hr10 / (10.0 / max(catalogue_size, 1)), 1)

    coverage = round(len(all_recommended) / max(catalogue_size, 1), 6)

    return {
        "history_limit": history_limit,
        "n_users": n,
        "accuracy": {
            "hit_rate_at_5": _avg(hr5_scores),
            "hit_rate_at_10": avg_hr10,
            "hit_rate_at_20": _avg(hr20_scores),
            "ndcg_at_10": _avg(ndcg_scores),
            "mrr": _avg(mrr_scores),
        },
        "beyond_accuracy": {
            "genre_precision_at_10": _avg(genre_prec_scores),
            "catalog_coverage": coverage,
            "novelty": _avg(novelty_scores),
            "intra_list_diversity": _avg(ild_scores),
        },
        "baselines": {
            "random_hit_rate_at_10": avg_random,
            "popularity_hit_rate_at_10": _avg(pop_hr10),
            "improvement_vs_random_x": improvement_x,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description="Offline evaluation: accuracy + beyond-accuracy")
    parser.add_argument("--max-users", type=int, default=500)
    parser.add_argument("--min-likes", type=int, default=3)
    parser.add_argument("--artifacts-dir", type=str, default=None)
    parser.add_argument("--output-path", type=str, default=None)
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = args.artifacts_dir or os.environ.get("ARTIFACTS_DIR", "/artifacts")
    cf_threshold = int(os.environ.get("CF_THRESHOLD", str(_DEFAULT_CF_THRESHOLD)))
    cf_alpha = float(os.environ.get("CF_ALPHA", str(_DEFAULT_CF_ALPHA)))

    from pymongo import AsyncMongoClient

    logger.info(f"Connecting to MongoDB: {mongo_uri}, db={db_name}")
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Load artifacts
    nlp_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    logger.info(f"Loading NLP artifact: {nlp_path}")
    nlp_data = joblib.load(nlp_path)

    cf_path = os.path.join(artifacts_dir, "cf_index.joblib")
    cf_data: dict | None = None
    if os.path.exists(cf_path):
        logger.info(f"Loading CF artifact: {cf_path}")
        cf_data = joblib.load(cf_path)
    else:
        logger.info("CF artifact not found — content-only mode")

    # Fetch catalogue metadata (genres + vote_count for novelty/diversity)
    logger.info("Fetching catalogue metadata ...")
    cat_cursor = db.movies.find(
        {},
        {"tmdb_id": 1, "genres": 1, "vote_count": 1},
    )
    cat_docs = await cat_cursor.to_list(length=None)
    catalogue_size = len(cat_docs)

    movie_genres: dict[int, set[str]] = {
        d["tmdb_id"]: set(d.get("genres") or []) for d in cat_docs
    }

    # Popularity rank: rank 1 = most popular
    sorted_by_pop = sorted(cat_docs, key=lambda d: d.get("vote_count") or 0, reverse=True)
    popularity_rank: dict[int, int] = {
        d["tmdb_id"]: i + 1 for i, d in enumerate(sorted_by_pop)
    }
    popularity_ids: list[int] = [d["tmdb_id"] for d in sorted_by_pop[:200]]
    all_popularity_ids: list[int] = [d["tmdb_id"] for d in sorted_by_pop]

    # Fetch user genre preferences
    logger.info("Fetching user preferences ...")
    pref_cursor = db.user_preferences.find({}, {"user_id": 1, "genres": 1})
    pref_docs = await pref_cursor.to_list(length=None)
    user_pref_genres: dict[str, set[str]] = {
        d["user_id"]: set(d.get("genres") or []) for d in pref_docs
    }
    logger.info(f"Loaded preferences for {len(user_pref_genres)} users")

    # Fetch interactions
    logger.info("Querying seed_user interactions ...")
    cursor = db.interactions.find({"user_id": {"$regex": "^seed_user_"}})
    interactions = await cursor.to_list(length=None)
    logger.info(f"Loaded {len(interactions)} interactions")

    test_set = build_leave_one_out_test_set(
        interactions, min_likes=args.min_likes, max_users=args.max_users
    )
    logger.info(f"Test set: {len(test_set)} users (min_likes={args.min_likes})")

    if not test_set:
        logger.warning("No qualifying users — aborting")
        await client.aclose()
        return

    # Run evaluation at each cold-start history limit
    cold_start_results: list[dict] = []
    for limit in _COLD_START_LIMITS:
        label = f"limit={limit}" if limit else "full history"
        logger.info(f"--- Evaluating: {label} ---")
        result = run_evaluation_pass(
            test_set=test_set,
            nlp_data=nlp_data,
            cf_data=cf_data,
            cf_threshold=cf_threshold,
            cf_alpha=cf_alpha,
            movie_genres=movie_genres,
            user_pref_genres=user_pref_genres,
            popularity_rank=popularity_rank,
            popularity_ids=popularity_ids,
            catalogue_size=catalogue_size,
            history_limit=limit,
        )
        cold_start_results.append(result)
        acc = result["accuracy"]
        ba = result["beyond_accuracy"]
        bl = result["baselines"]
        logger.info(
            f"  HR@5={acc['hit_rate_at_5']:.4f}  HR@10={acc['hit_rate_at_10']:.4f}"
            f"  HR@20={acc['hit_rate_at_20']:.4f}  NDCG@10={acc['ndcg_at_10']:.4f}"
            f"  MRR={acc['mrr']:.4f}"
        )
        logger.info(
            f"  GenrePrec@10={ba['genre_precision_at_10']:.4f}"
            f"  Coverage={ba['catalog_coverage']:.4f}"
            f"  Novelty={ba['novelty']:.4f}"
            f"  ILD={ba['intra_list_diversity']:.4f}"
        )
        logger.info(
            f"  vs Random={bl['random_hit_rate_at_10']:.4f}"
            f"  vs Pop={bl['popularity_hit_rate_at_10']:.4f}"
            f"  Improvement={bl['improvement_vs_random_x']:.1f}x"
        )

    # Baseline comparison: 4 strategies at full history
    logger.info("--- Running baseline comparison (full history, all strategies) ---")
    strategies = ["popular", "content", "cf", "hybrid"] if cf_data else ["popular", "content", "hybrid"]
    baseline_comparison: list[dict] = []
    for strat in strategies:
        res = run_strategy_pass(
            test_set=test_set,
            strategy=strat,
            nlp_data=nlp_data,
            cf_data=cf_data,
            cf_threshold=cf_threshold,
            cf_alpha=cf_alpha,
            movie_genres=movie_genres,
            user_pref_genres=user_pref_genres,
            popularity_rank=popularity_rank,
            all_popularity_ids=all_popularity_ids,
            catalogue_size=catalogue_size,
        )
        baseline_comparison.append(res)
        logger.info(
            f"  {strat:10s}: P@10={res['precision_at_10']:.4f}"
            f"  NDCG@10={res['ndcg_at_10']:.4f}"
            f"  MRR={res['mrr']:.4f}"
            f"  GenrePrec={res['genre_precision_at_10']:.4f}"
            f"  Coverage={res['catalog_coverage']:.4f}"
        )

    # Full-history result is the last entry (limit=None)
    full = cold_start_results[-1]

    output = {
        "eval_date": date.today().isoformat(),
        "catalogue_size": catalogue_size,
        "summary": full,
        "cold_start_curve": cold_start_results,
        "baseline_comparison": baseline_comparison,
        # Top-level flat keys for backward compatibility
        "hit_rate_at_10": full["accuracy"]["hit_rate_at_10"],
        "hit_rate_at_5": full["accuracy"]["hit_rate_at_5"],
        "hit_rate_at_20": full["accuracy"]["hit_rate_at_20"],
        "ndcg_at_10": full["accuracy"]["ndcg_at_10"],
        "mrr": full["accuracy"]["mrr"],
        "baselines": full["baselines"],
        "improvement_vs_random_x": full["baselines"]["improvement_vs_random_x"],
        "n_users": full["n_users"],
        "history_limit": None,
    }

    output_path = args.output_path or os.path.join(artifacts_dir, "metrics.json")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"\nMetrics written to: {output_path}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
