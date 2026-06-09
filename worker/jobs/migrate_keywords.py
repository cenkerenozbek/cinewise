"""Migration: backfill tagline and keywords for all existing movies.

Fetches /movie/{id}?append_to_response=keywords from TMDB for every movie
that is missing tagline or keywords, then updates the MongoDB document.

Usage:
    python jobs/migrate_keywords.py [--batch-size 50] [--dry-run]
"""

import argparse
import asyncio
import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipelines.fetch_movies import fetch_tmdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

_SEMAPHORE_LIMIT = 20  # concurrent TMDB requests


async def fetch_keywords_and_tagline(
    client: httpx.AsyncClient,
    movie_id: int,
    sem: asyncio.Semaphore,
) -> tuple[int, list[str], str | None]:
    async with sem:
        data = await fetch_tmdb(
            client,
            f"/movie/{movie_id}",
            {"append_to_response": "keywords"},
        )
    keywords = [kw["name"] for kw in data.get("keywords", {}).get("keywords", [])]
    tagline = data.get("tagline") or None
    return movie_id, keywords, tagline


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    tmdb_api_key = os.environ.get("TMDB_API_KEY")

    if not tmdb_api_key:
        logger.error("TMDB_API_KEY not set")
        sys.exit(1)

    client_mongo = AsyncMongoClient(mongo_uri)
    db = client_mongo[db_name]

    # Only process movies missing keywords or tagline
    cursor = db.movies.find(
        {"$or": [
            {"keywords": {"$exists": False}},
            {"tagline": {"$exists": False}},
        ]},
        {"tmdb_id": 1},
    )
    docs = await cursor.to_list(length=None)
    tmdb_ids = [d["tmdb_id"] for d in docs]
    logger.info(f"Movies to backfill: {len(tmdb_ids)}")

    if not tmdb_ids:
        logger.info("Nothing to backfill.")
        await client_mongo.aclose()
        return

    sem = asyncio.Semaphore(_SEMAPHORE_LIMIT)
    success = errors = 0

    async with httpx.AsyncClient(
        params={"api_key": tmdb_api_key}, timeout=30.0
    ) as http:
        for batch_start in range(0, len(tmdb_ids), args.batch_size):
            batch = tmdb_ids[batch_start: batch_start + args.batch_size]
            tasks = [fetch_keywords_and_tagline(http, mid, sem) for mid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            bulk_ops = []
            for res in results:
                if isinstance(res, Exception):
                    errors += 1
                    logger.warning(f"Fetch error: {res}")
                    continue
                movie_id, keywords, tagline = res
                if not args.dry_run:
                    from pymongo import UpdateOne
                    bulk_ops.append(UpdateOne(
                        {"tmdb_id": movie_id},
                        {"$set": {"keywords": keywords, "tagline": tagline}},
                    ))
                success += 1

            if bulk_ops and not args.dry_run:
                await db.movies.bulk_write(bulk_ops, ordered=False)

            done = min(batch_start + args.batch_size, len(tmdb_ids))
            logger.info(f"Progress: {done}/{len(tmdb_ids)} — success={success} errors={errors}")

    logger.info(f"Migration complete: {success} updated, {errors} errors")
    await client_mongo.aclose()


if __name__ == "__main__":
    asyncio.run(main())
