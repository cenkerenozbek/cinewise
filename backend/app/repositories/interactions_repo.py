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

    async def upsert(self, user_id: str, movie_id: int, action: str) -> None:
        """Insert or replace the user's feedback for a specific movie (upsert semantics)."""
        await self.collection.update_one(
            {"user_id": user_id, "movie_id": movie_id},
            {"$set": {
                "user_id": user_id,
                "movie_id": movie_id,
                "action": action,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    async def get_by_user_id(self, user_id: str) -> list[dict]:
        """Return all interaction documents for the given user."""
        cursor = self.collection.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def count_by_user_id(self, user_id: str) -> int:
        """Return the number of interaction documents for the given user."""
        return await self.collection.count_documents({"user_id": user_id})
