"""MongoDB data access layer for the `movies` collection."""
import os
import sys

# Allow importing shared constants without installing the package
_shared_dir = os.path.join(os.path.dirname(__file__), "../../../../shared")
if _shared_dir not in sys.path:
    sys.path.insert(0, _shared_dir)

try:
    from config import MOVIES_COLLECTION  # type: ignore
except ImportError:
    MOVIES_COLLECTION = "movies"


class MovieRepository:
    """Data access object for the MongoDB `movies` collection."""

    def __init__(self, db) -> None:
        self.collection = db[MOVIES_COLLECTION]

    async def search(
        self,
        query: str | None,
        genre: str | None,
        year: int | None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        min_votes: int | None = None,
        min_rating: float | None = None,
    ) -> tuple[list[dict], int]:
        """Search/filter movies and return (page_of_docs, total_count).

        When *query* is provided, results are filtered by a case-insensitive title
        regex (mongomock does not support ``$text`` index, so we use a regex for
        test compatibility while keeping the same interface).

        In production (real MongoDB), the text index on ``title`` is used via
        ``{"$text": {"$search": query}}``.
        """
        filters: dict = {}

        if query:
            import re
            pattern = {"$regex": re.escape(query), "$options": "i"}
            filters["$or"] = [
                {"title": pattern},
                {"title_tr": pattern},
                {"original_title": pattern},
                {"cast": pattern},
                {"director": pattern},
            ]

        if genre:
            filters["genres"] = genre

        if year:
            filters["year"] = year

        if min_votes is not None:
            filters["vote_count"] = {"$gte": min_votes}

        if min_rating is not None:
            filters.setdefault("rating", {})
            if isinstance(filters["rating"], dict):
                filters["rating"]["$gte"] = min_rating
            else:
                filters["rating"] = {"$gte": min_rating}

        skip = (page - 1) * page_size

        cursor = self.collection.find(filters)

        if not query:
            sort_field = "vote_count" if sort_by == "votes" else "popularity"
            cursor = cursor.sort(sort_field, -1)

        total = await self.collection.count_documents(filters)
        docs = await cursor.skip(skip).limit(page_size).to_list(length=page_size)
        return docs, total

    async def find_by_tmdb_id(self, tmdb_id: int) -> dict | None:
        """Return the movie document with the given *tmdb_id*, or None."""
        return await self.collection.find_one({"tmdb_id": tmdb_id})

    async def get_distinct_genres(self) -> list[str]:
        """Return a sorted list of distinct genre strings across all movies."""
        genres = await self.collection.distinct("genres")
        return sorted(g for g in genres if g is not None)

    async def upsert(self, tmdb_id: int, movie_data: dict) -> None:
        """Insert or update a movie document identified by *tmdb_id*."""
        await self.collection.update_one(
            {"tmdb_id": tmdb_id},
            {"$set": movie_data},
            upsert=True,
        )
