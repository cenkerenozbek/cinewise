"""Business logic for movie browsing and search."""
from fastapi import HTTPException, status

from app.models.movie import GenresResponse, MovieDetail, MovieListResponse, MovieSummary
from app.repositories.movie_repo import MovieRepository


class MovieService:
    """Thin business logic layer over MovieRepository."""

    def __init__(self, db) -> None:
        self._repo = MovieRepository(db)

    async def list_movies(
        self,
        query: str | None,
        genre: str | None,
        year: int | None,
        page: int,
        page_size: int,
    ) -> MovieListResponse:
        """Return a paginated list of movies matching the given filters."""
        docs, total = await self._repo.search(query, genre, year, page, page_size)
        movies = [MovieSummary(**_to_summary(doc)) for doc in docs]
        return MovieListResponse(movies=movies, total=total, page=page, page_size=page_size)

    async def get_movie(self, tmdb_id: int) -> MovieDetail:
        """Return full movie detail for *tmdb_id*.

        Raises:
            HTTPException 404: if the movie is not found.
        """
        doc = await self._repo.find_by_tmdb_id(tmdb_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with tmdb_id={tmdb_id} not found",
            )
        return MovieDetail(**_to_detail(doc))

    async def get_genres(self) -> GenresResponse:
        """Return the sorted list of distinct genres."""
        genres = await self._repo.get_distinct_genres()
        return GenresResponse(genres=genres)


# ---------------------------------------------------------------------------
# Internal helpers — map raw MongoDB documents to Pydantic-compatible dicts
# ---------------------------------------------------------------------------

def _to_summary(doc: dict) -> dict:
    """Extract MovieSummary fields from a MongoDB document."""
    return {
        "tmdb_id": doc["tmdb_id"],
        "title": doc.get("title", ""),
        "title_tr": doc.get("title_tr"),
        "year": doc.get("year"),
        "genres": doc.get("genres", []),
        "poster_path": doc.get("poster_path"),
        "rating": doc.get("rating"),
    }


def _to_detail(doc: dict) -> dict:
    """Extract MovieDetail fields from a MongoDB document."""
    return {
        **_to_summary(doc),
        "overview": doc.get("overview"),
        "vote_count": doc.get("vote_count"),
        "popularity": doc.get("popularity"),
        "director": doc.get("director"),
        "cast": doc.get("cast", []),
    }
