"""MovieLens-20M interaction seeding script.

Downloads and processes MovieLens-20M links.csv and ratings.csv, maps
MovieLens movie IDs to TMDB IDs, filters ratings into like/dislike
interactions, and inserts synthetic interactions for a bounded subset of
users into the MongoDB interactions collection.

Seeded users are namespaced as seed_user_{userId} to distinguish them from
real application users. The operation is idempotent — existing seed_user_*
interactions are deleted before each run.

Usage:
    python jobs/seed_interactions.py

Environment variables:
    MONGO_URI          MongoDB connection string (default: mongodb://localhost:27017)
    DB_NAME            Database name (default: movie_mrs)
    MOVIELENS_DIR      Path to directory containing links.csv and ratings.csv
                       (default: /data/movielens)
    SEED_USER_LIMIT    Maximum number of unique MovieLens user IDs to process
                       (default: 1000)
"""

import asyncio
import csv
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

# Add project root to path so shared/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Rating thresholds for like/dislike classification
LIKE_THRESHOLD = 4.0
DISLIKE_THRESHOLD = 2.0

# Batch size for insert_many operations
INSERT_BATCH_SIZE = 5000


def load_links_mapping(links_path: str) -> dict[int, int]:
    """Build a MovieLens movieId -> tmdbId mapping from links.csv.

    Skips rows where tmdbId is empty, whitespace-only, or non-numeric.

    Args:
        links_path: Absolute path to links.csv.

    Returns:
        Dict mapping MovieLens integer movieId to integer TMDB ID.
    """
    ml_to_tmdb: dict[int, int] = {}
    with open(links_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tmdb_raw = row.get("tmdbId", "").strip()
            if not tmdb_raw:
                continue
            try:
                tmdb_id = int(float(tmdb_raw))  # handles "12345.0" format
                ml_movie_id = int(row["movieId"])
                ml_to_tmdb[ml_movie_id] = tmdb_id
            except (ValueError, KeyError):
                continue
    logger.info(f"Loaded {len(ml_to_tmdb)} MovieLens->TMDB ID mappings from links.csv")
    return ml_to_tmdb


def classify_rating(rating: float) -> str | None:
    """Classify a numeric rating as 'like', 'dislike', or None (ambiguous).

    Args:
        rating: Numeric rating value.

    Returns:
        'like' if rating >= LIKE_THRESHOLD, 'dislike' if rating <= DISLIKE_THRESHOLD,
        None for ambiguous ratings in between.
    """
    if rating >= LIKE_THRESHOLD:
        return "like"
    if rating <= DISLIKE_THRESHOLD:
        return "dislike"
    return None


def build_interactions(
    ratings_path: str,
    ml_to_tmdb: dict[int, int],
    existing_tmdb_ids: set[int],
    seed_user_limit: int,
) -> list[dict]:
    """Parse ratings.csv and build interaction documents for seed users.

    Processes ratings in order, limiting to the first `seed_user_limit` unique
    MovieLens user IDs encountered. Filters by rating threshold and only
    includes movies present in existing_tmdb_ids.

    Args:
        ratings_path: Absolute path to ratings.csv.
        ml_to_tmdb: MovieLens movieId -> tmdbId mapping.
        existing_tmdb_ids: Set of TMDB IDs that exist in our movies collection.
        seed_user_limit: Maximum number of unique MovieLens user IDs to include.

    Returns:
        List of interaction dicts ready for MongoDB insertion.
    """
    interactions: list[dict] = []
    seen_users: dict[int, bool] = {}

    with open(ratings_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ml_user_id = int(row["userId"])
                ml_movie_id = int(row["movieId"])
                rating = float(row["rating"])
                ts = datetime.fromtimestamp(float(row["timestamp"]), tz=timezone.utc)
            except (ValueError, KeyError):
                continue

            # Enforce user limit
            if ml_user_id not in seen_users:
                if len(seen_users) >= seed_user_limit:
                    continue
                seen_users[ml_user_id] = True

            # Map to TMDB ID
            tmdb_id = ml_to_tmdb.get(ml_movie_id)
            if tmdb_id is None:
                continue

            # Only include movies we actually have in our DB
            if tmdb_id not in existing_tmdb_ids:
                continue

            # Classify rating
            action = classify_rating(rating)
            if action is None:
                continue

            interactions.append({
                "user_id": f"seed_user_{ml_user_id}",
                "movie_id": tmdb_id,
                "action": action,
                "updated_at": ts,
            })

    logger.info(
        f"Built {len(interactions)} interactions for {len(seen_users)} seed users"
    )
    return interactions


async def main() -> None:
    """Orchestrate MovieLens seeding: load CSVs -> filter -> insert interactions."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    movielens_dir = os.environ.get("MOVIELENS_DIR", "/data/movielens")
    seed_user_limit = int(os.environ.get("SEED_USER_LIMIT", "1000"))

    links_path = os.path.join(movielens_dir, "links.csv")
    ratings_path = os.path.join(movielens_dir, "ratings.csv")

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Step 1: Build MovieLens -> TMDB ID mapping from links.csv
    ml_to_tmdb = load_links_mapping(links_path)

    # Step 2: Get set of TMDB IDs that exist in our movies collection
    logger.info("Querying existing movie TMDB IDs from MongoDB...")
    cursor = db.movies.find({}, {"tmdb_id": 1, "_id": 0})
    movie_docs = await cursor.to_list(length=None)
    existing_tmdb_ids = {doc["tmdb_id"] for doc in movie_docs}
    logger.info(f"Found {len(existing_tmdb_ids)} movies in DB")

    # Step 3: Build interactions from ratings.csv
    interactions = build_interactions(
        ratings_path, ml_to_tmdb, existing_tmdb_ids, seed_user_limit
    )

    if not interactions:
        logger.warning("No interactions to seed — check MOVIELENS_DIR and movies collection")
        await client.aclose()
        return

    # Step 4: Idempotent cleanup — delete all existing seed interactions
    logger.info("Deleting existing seed_user_* interactions for idempotent re-run...")
    delete_result = await db.interactions.delete_many(
        {"user_id": {"$regex": "^seed_user_"}}
    )
    logger.info(f"Deleted {delete_result.deleted_count} existing seed interactions")

    # Step 5: Batch insert in chunks of INSERT_BATCH_SIZE
    total_inserted = 0
    for i in range(0, len(interactions), INSERT_BATCH_SIZE):
        batch = interactions[i : i + INSERT_BATCH_SIZE]
        await db.interactions.insert_many(batch)
        total_inserted += len(batch)
        logger.info(f"Inserted batch {i // INSERT_BATCH_SIZE + 1}: {total_inserted}/{len(interactions)}")

    # Collect stats for final log
    unique_users = len({doc["user_id"] for doc in interactions})
    unique_movies = len({doc["movie_id"] for doc in interactions})
    logger.info(
        f"Seeded {total_inserted} interactions for {unique_users} users across {unique_movies} movies"
    )

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
