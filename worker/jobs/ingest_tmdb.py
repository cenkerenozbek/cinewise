"""Main entry point for TMDB batch movie ingestion."""

import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

# Add project root to path so shared/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.config import MOVIES_COLLECTION
from pipelines.fetch_movies import fetch_movie_ids, fetch_movie_details
from pipelines.transform import transform_movie
from pipelines.load import upsert_movie

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    """Orchestrate TMDB batch ingestion: fetch -> transform -> upsert."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    tmdb_api_key = os.environ.get("TMDB_API_KEY")

    if not tmdb_api_key:
        logger.error("TMDB_API_KEY not set in environment. Exiting.")
        sys.exit(1)

    target_count = int(os.environ.get("TMDB_TARGET_COUNT", "5000"))

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]
    collection = db[MOVIES_COLLECTION]

    start_time = time.time()

    async with httpx.AsyncClient(
        params={"api_key": tmdb_api_key}, timeout=30.0
    ) as http_client:
        logger.info(f"Fetching movie IDs (target: {target_count})...")
        movie_ids = await fetch_movie_ids(http_client, target_count=target_count)
        logger.info(f"Found {len(movie_ids)} unique movie IDs")

        existing = await collection.distinct("tmdb_id", {"tmdb_id": {"$in": movie_ids}})
        existing_set = set(existing)
        new_ids = [mid for mid in movie_ids if mid not in existing_set]
        logger.info(f"Skipping {len(existing_set)} existing movies, ingesting {len(new_ids)} new")

        if not new_ids:
            logger.info("Nothing new to ingest. Sleeping 6 hours.")
            client.close()
            await asyncio.sleep(6 * 3600)
            return

        success = 0
        errors = 0
        for i, movie_id in enumerate(new_ids, 1):
            try:
                details = await fetch_movie_details(http_client, movie_id)
                movie_doc = transform_movie(details)
                await upsert_movie(collection, movie_doc)
                success += 1
            except Exception as e:
                errors += 1
                logger.error(f"Failed to ingest movie {movie_id}: {e}")

            if i % 100 == 0:
                elapsed = time.time() - start_time
                logger.info(
                    f"Progress: {i}/{len(new_ids)} | "
                    f"Success: {success} | Errors: {errors} | "
                    f"Elapsed: {elapsed:.0f}s"
                )

    elapsed = time.time() - start_time
    logger.info(
        f"Ingestion complete: {success} movies ingested, {errors} errors, "
        f"{elapsed:.0f}s elapsed"
    )
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
