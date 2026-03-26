"""MongoDB data access layer for the `user_preferences` collection."""
import os
import sys
from datetime import datetime, timezone

_shared_dir = os.path.join(os.path.dirname(__file__), "../../../../shared")
if _shared_dir not in sys.path:
    sys.path.insert(0, _shared_dir)

try:
    from config import USER_PREFERENCES_COLLECTION  # type: ignore
except ImportError:
    USER_PREFERENCES_COLLECTION = "user_preferences"


class UserPreferencesRepository:
    """Data access object for the MongoDB `user_preferences` collection."""

    def __init__(self, db) -> None:
        self.collection = db[USER_PREFERENCES_COLLECTION]

    async def get_by_user_id(self, user_id: str) -> dict | None:
        """Return the preferences document for user_id, or None."""
        return await self.collection.find_one({"user_id": user_id})

    async def upsert(self, user_id: str, genres: list[str], mood: str | None) -> None:
        """Insert or update preferences for user_id."""
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "genres": genres,
                "mood": mood,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
