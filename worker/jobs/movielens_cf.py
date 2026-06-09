"""MovieLens 20M → CF artifact pipeline.

Downloads real user interaction data from MovieLens 20M and builds a
high-quality CF index to replace the synthetic seed-user CF artifact.

Steps:
  1. Load links.csv  → MovieLens movieId → TMDB ID mapping
  2. Load ratings.csv → 20M user–movie ratings
  3. Filter to movies present in our catalog (via NLP artifact tmdb_ids)
  4. Convert ratings to implicit signals: ≥ threshold → like, ≤ low → dislike
  5. Build SVD-based item-item CF index (reuses cf_features.build_cf_index)
  6. Save as cf_index.joblib (replaces existing artifact)

Usage:
    python jobs/movielens_cf.py \\
        --data-dir /data/movielens/ml-20m \\
        [--artifacts-dir /artifacts] \\
        [--like-threshold 3.5] \\
        [--dislike-threshold 2.0] \\
        [--top-n 50]

Download MovieLens 20M:
    https://grouplens.org/datasets/movielens/20m/
    Extract the zip so that ml-20m/ratings.csv and ml-20m/links.csv exist.
"""

import argparse
import logging
import os
import sys

import joblib
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_tmdb_mapping(links_path: str) -> dict[int, int]:
    """Return {movielens_movie_id: tmdb_id} from links.csv.

    Rows with missing/zero tmdbId are skipped.
    """
    import pandas as pd

    links = pd.read_csv(links_path, dtype={"movieId": int, "tmdbId": "Int64"})
    links = links.dropna(subset=["tmdbId"])
    links = links[links["tmdbId"] > 0]
    mapping = dict(zip(links["movieId"].astype(int), links["tmdbId"].astype(int)))
    logger.info(f"links.csv: {len(mapping):,} movieId→tmdbId mappings loaded")
    return mapping


def load_interactions(
    ratings_path: str,
    ml_to_tmdb: dict[int, int],
    catalog_tmdb_ids: set[int],
    like_threshold: float,
    dislike_threshold: float,
) -> list[dict]:
    """Read ratings.csv and convert to interaction dicts.

    Rating ≥ like_threshold  → action='like'
    Rating ≤ dislike_threshold → action='dislike'
    Ratings in between are skipped (neutral signal).

    Only rows whose tmdbId appears in catalog_tmdb_ids are kept.
    Returns list of {user_id, movie_id, action}.
    """
    import pandas as pd

    logger.info(f"Reading {ratings_path} ...")
    ratings = pd.read_csv(
        ratings_path,
        dtype={"userId": int, "movieId": int, "rating": float},
        usecols=["userId", "movieId", "rating"],
    )
    logger.info(f"Loaded {len(ratings):,} raw ratings")

    # Map to TMDB IDs
    ratings["tmdb_id"] = ratings["movieId"].map(ml_to_tmdb)
    ratings = ratings.dropna(subset=["tmdb_id"])
    ratings["tmdb_id"] = ratings["tmdb_id"].astype(int)

    # Filter to catalog
    ratings = ratings[ratings["tmdb_id"].isin(catalog_tmdb_ids)]
    logger.info(f"After catalog filter: {len(ratings):,} ratings covering "
                f"{ratings['tmdb_id'].nunique():,} movies and "
                f"{ratings['userId'].nunique():,} users")

    # Assign action
    likes = ratings[ratings["rating"] >= like_threshold].copy()
    likes["action"] = "like"
    dislikes = ratings[ratings["rating"] <= dislike_threshold].copy()
    dislikes["action"] = "dislike"
    filtered = pd.concat([likes, dislikes], ignore_index=True)
    logger.info(
        f"Signal split: {len(likes):,} likes / {len(dislikes):,} dislikes "
        f"(neutral skipped: {len(ratings) - len(likes) - len(dislikes):,})"
    )

    interactions = [
        {"user_id": str(row.userId), "movie_id": int(row.tmdb_id), "action": row.action}
        for row in filtered.itertuples(index=False)
    ]
    return interactions


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CF artifact from MovieLens 20M")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("MOVIELENS_DIR", "/data/movielens/ml-20m"),
        help="Path to extracted ml-20m directory containing ratings.csv and links.csv",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=os.environ.get("ARTIFACTS_DIR", "/artifacts"),
    )
    parser.add_argument("--like-threshold", type=float, default=3.5,
                        help="Ratings >= this are treated as 'like'")
    parser.add_argument("--dislike-threshold", type=float, default=2.0,
                        help="Ratings <= this are treated as 'dislike'")
    parser.add_argument("--top-n", type=int, default=50,
                        help="CF neighbours to store per movie")
    args = parser.parse_args()

    links_path = os.path.join(args.data_dir, "links.csv")
    ratings_path = os.path.join(args.data_dir, "ratings.csv")

    for p in [links_path, ratings_path]:
        if not os.path.exists(p):
            logger.error(f"File not found: {p}")
            logger.error(
                "Download MovieLens 20M from https://grouplens.org/datasets/movielens/20m/ "
                "and extract so that ml-20m/ratings.csv and ml-20m/links.csv exist, "
                f"then pass --data-dir pointing to the ml-20m folder."
            )
            sys.exit(1)

    # Load canonical movie list from NLP artifact
    nlp_path = os.path.join(args.artifacts_dir, "similarity_index.joblib")
    if not os.path.exists(nlp_path):
        logger.error(f"NLP artifact not found at {nlp_path}. Run nlp_features.py first.")
        sys.exit(1)

    logger.info("Loading NLP artifact for canonical tmdb_ids ...")
    sim_data = joblib.load(nlp_path)
    tmdb_ids: list[int] = sim_data["tmdb_ids"]
    catalog_set = set(tmdb_ids)
    logger.info(f"Catalog size: {len(tmdb_ids):,} movies")

    # Build MovieLens → TMDB mapping and load interactions
    ml_to_tmdb = load_tmdb_mapping(links_path)
    interactions = load_interactions(
        ratings_path,
        ml_to_tmdb,
        catalog_set,
        args.like_threshold,
        args.dislike_threshold,
    )
    logger.info(f"Total interactions for CF training: {len(interactions):,}")

    if not interactions:
        logger.error("No interactions after filtering — check data-dir and catalog overlap.")
        sys.exit(1)

    # Import here to avoid circular imports when testing
    from jobs.cf_features import build_cf_index, save_cf_artifacts

    logger.info(f"Building CF index (top_n={args.top_n}) ...")
    cf_top_indices, cf_top_scores = build_cf_index(interactions, tmdb_ids, top_n=args.top_n)
    logger.info(f"CF index shape: {cf_top_indices.shape}")

    save_cf_artifacts(tmdb_ids, cf_top_indices, cf_top_scores, args.artifacts_dir)
    logger.info("MovieLens CF pipeline complete.")


if __name__ == "__main__":
    main()
