"""MongoDB data access layer for the `users` collection."""
from datetime import datetime, timezone

from sys import path as _sys_path
import os as _os

# Allow importing shared constants without installing the package
_shared_dir = _os.path.join(_os.path.dirname(__file__), "../../../../shared")
if _shared_dir not in _sys_path:
    _sys_path.insert(0, _shared_dir)

try:
    from config import USERS_COLLECTION  # type: ignore
except ImportError:
    USERS_COLLECTION = "users"


class UserRepository:
    """Data access object for the MongoDB `users` collection."""

    def __init__(self, db) -> None:
        self.collection = db[USERS_COLLECTION]

    async def find_by_email(self, email: str) -> dict | None:
        """Return the user document matching *email*, or None if not found."""
        return await self.collection.find_one({"email": email})

    async def create(self, user_data: dict) -> str:
        """Insert *user_data* and return the new document's ID as a string."""
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)

    async def find_by_id(self, user_id: str) -> dict | None:
        from bson import ObjectId
        return await self.collection.find_one({"_id": ObjectId(user_id)})

    async def update_profile(self, user_id: str, fields: dict) -> None:
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": fields},
        )
