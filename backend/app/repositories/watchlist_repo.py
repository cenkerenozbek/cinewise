"""MongoDB data access layer for the `watchlists` collection."""
from datetime import datetime, timezone


class WatchlistRepository:
    """Data access object for the MongoDB `watchlists` collection."""

    def __init__(self, db) -> None:
        self.collection = db["watchlists"]

    async def add(self, user_id: str, movie_id: int) -> None:
        """Add a movie to the user's watchlist (idempotent)."""
        await self.collection.update_one(
            {"user_id": user_id, "movie_id": movie_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "movie_id": movie_id,
                "added_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    async def remove(self, user_id: str, movie_id: int) -> None:
        """Remove a movie from the user's watchlist."""
        await self.collection.delete_one({"user_id": user_id, "movie_id": movie_id})

    async def get_by_user_id(self, user_id: str) -> list[dict]:
        """Return all watchlist entries for the given user."""
        cursor = self.collection.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def contains(self, user_id: str, movie_id: int) -> bool:
        """Return True if movie is in the user's watchlist."""
        doc = await self.collection.find_one({"user_id": user_id, "movie_id": movie_id})
        return doc is not None
