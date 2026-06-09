"""One-time migration: add original_language to existing movie documents."""

import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.config import MOVIES_COLLECTION
from pipelines.fetch_movies import fetch_movie_details

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

BATCH_SIZE = 50
RATE_LIMIT_DELAY = 0.05  # 50ms between requests — stays within TMDB free tier


async def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    tmdb_api_key = os.environ.get("TMDB_API_KEY")

    if not tmdb_api_key:
        logger.error("TMDB_API_KEY not set. Exiting.")
        sys.exit(1)

    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]
    collection = db[MOVIES_COLLECTION]

    cursor = collection.find(
        {"original_language": {"$exists": False}},
        {"tmdb_id": 1, "_id": 1}
    )
    movies = await cursor.to_list(length=None)
    total = len(movies)
    logger.info(f"Found {total} movies without original_language")

    if total == 0:
        logger.info("All movies already have original_language. Nothing to do.")
        client.close()
        return

    updated = 0
    errors = 0
    start = time.time()

    async with httpx.AsyncClient(params={"api_key": tmdb_api_key}, timeout=30.0) as http:
        for i, doc in enumerate(movies, 1):
            tmdb_id = doc["tmdb_id"]
            try:
                details = await fetch_movie_details(http, tmdb_id)
                lang = details.get("original_language")
                await collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"original_language": lang}}
                )
                updated += 1
            except Exception as e:
                errors += 1
                logger.warning(f"Failed for tmdb_id={tmdb_id}: {e}")

            await asyncio.sleep(RATE_LIMIT_DELAY)

            if i % BATCH_SIZE == 0:
                elapsed = time.time() - start
                rate = i / elapsed
                remaining = (total - i) / rate if rate > 0 else 0
                logger.info(
                    f"{i}/{total} | updated={updated} errors={errors} | "
                    f"~{remaining:.0f}s remaining"
                )

    elapsed = time.time() - start
    logger.info(f"Done: {updated} updated, {errors} errors, {elapsed:.0f}s")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
