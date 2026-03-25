"""MongoDB upsert operations for movie documents."""

from datetime import datetime, timezone


async def upsert_movie(collection, movie_doc: dict):
    """Upsert movie document by tmdb_id."""
    movie_doc["ingested_at"] = datetime.now(timezone.utc)
    await collection.update_one(
        {"tmdb_id": movie_doc["tmdb_id"]},
        {"$set": movie_doc},
        upsert=True,
    )


async def upsert_batch(collection, movie_docs: list[dict]):
    """Upsert a batch of movie documents."""
    from pymongo import UpdateOne
    if not movie_docs:
        return
    ops = [
        UpdateOne(
            {"tmdb_id": doc["tmdb_id"]},
            {"$set": doc},
            upsert=True,
        )
        for doc in movie_docs
    ]
    await collection.bulk_write(ops, ordered=False)
