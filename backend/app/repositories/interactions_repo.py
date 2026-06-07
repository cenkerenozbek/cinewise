"""MongoDB data access layer for the `interactions` collection."""
import os
import sys
from datetime import datetime, timezone

_shared_dir = os.path.join(os.path.dirname(__file__), "../../../../shared")
if _shared_dir not in sys.path:
    sys.path.insert(0, _shared_dir)

try:
    from config import INTERACTIONS_COLLECTION  # type: ignore
except ImportError:
    INTERACTIONS_COLLECTION = "interactions"


class InteractionsRepository:
    """Data access object for the MongoDB `interactions` collection."""

    def __init__(self, db) -> None:
        self.collection = db[INTERACTIONS_COLLECTION]

    async def upsert(
        self,
        user_id: str,
        movie_id: int,
        action: str,
        watch_completion: float | None = None,
    ) -> None:
        """Insert or replace the user's feedback for a specific movie (upsert semantics).

        Optional watch_completion stores how much of the movie was watched (0.0–1.0).
        """
        update_fields: dict = {
            "user_id": user_id,
            "movie_id": movie_id,
            "action": action,
            "updated_at": datetime.now(timezone.utc),
        }
        if watch_completion is not None:
            update_fields["watch_completion"] = watch_completion

        await self.collection.update_one(
            {"user_id": user_id, "movie_id": movie_id},
            {"$set": update_fields},
            upsert=True,
        )

    async def delete(self, user_id: str, movie_id: int) -> None:
        """Remove the user's feedback for a specific movie."""
        await self.collection.delete_one({"user_id": user_id, "movie_id": movie_id})

    async def get_by_user_id(self, user_id: str) -> list[dict]:
        """Return all interaction documents for the given user."""
        cursor = self.collection.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def count_by_user_id(self, user_id: str) -> int:
        """Return the number of interaction documents for the given user."""
        return await self.collection.count_documents({"user_id": user_id})

    async def get_stats_by_user_id(self, user_id: str) -> dict:
        """Return aggregated stats for a user's interactions."""
        interactions = await self.get_by_user_id(user_id)
        liked = [ia for ia in interactions if ia.get("action") == "like"]
        disliked = [ia for ia in interactions if ia.get("action") == "dislike"]
        completions = [ia["watch_completion"] for ia in interactions if ia.get("watch_completion") is not None]
        return {
            "total": len(interactions),
            "liked": len(liked),
            "disliked": len(disliked),
            "watched_count": len(completions),
            "avg_completion": sum(completions) / len(completions) if completions else None,
        }
