"""FastAPI router for movie endpoints.

Endpoints:
- GET /api/movies              — List and search movies with optional filters
- GET /api/movies/genres       — Return distinct genre list (must be before /{tmdb_id})
- GET /api/movies/{tmdb_id}    — Return full movie detail
- GET /api/movies/{tmdb_id}/trailer — Return YouTube trailer key from TMDB
"""
from fastapi import APIRouter, Depends
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.models.movie import GenresResponse, MovieDetail, MovieListResponse
from app.services.movie_service import MovieService

router = APIRouter(prefix="/api/movies", tags=["movies"])


def _get_movie_service(db=Depends(get_db)) -> MovieService:
    return MovieService(db)


@router.get("", response_model=MovieListResponse)
async def list_movies(
    q: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    page: int = 1,
    page_size: int = 20,
    service: MovieService = Depends(_get_movie_service),
) -> MovieListResponse:
    """Return a paginated list of movies.

    Query parameters:
    - **q**: Case-insensitive title search
    - **genre**: Filter to movies that include this genre
    - **year**: Filter to movies released in this year
    - **page**: Page number (default 1)
    - **page_size**: Results per page (default 20)
    """
    return await service.list_movies(q, genre, year, page, page_size)


@router.get("/genres", response_model=GenresResponse)
async def list_genres(
    service: MovieService = Depends(_get_movie_service),
) -> GenresResponse:
    """Return a sorted list of distinct genre strings across all movies."""
    return await service.get_genres()


@router.get("/{tmdb_id}/trailer")
async def get_movie_trailer(tmdb_id: int) -> dict:
    """Return the YouTube trailer key for a movie from TMDB. Returns null if not found."""
    if not settings.TMDB_API_KEY:
        return {"youtube_key": None}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos",
                params={"api_key": settings.TMDB_API_KEY, "language": "en-US"},
            )
            resp.raise_for_status()
            videos = resp.json().get("results", [])
            # Prefer official trailer, fall back to any trailer/teaser on YouTube
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") == "Trailer" and v.get("official"):
                    return {"youtube_key": v["key"]}
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                    return {"youtube_key": v["key"]}
    except Exception:
        pass
    return {"youtube_key": None}


@router.get("/{tmdb_id}", response_model=MovieDetail)
async def get_movie(
    tmdb_id: int,
    service: MovieService = Depends(_get_movie_service),
) -> MovieDetail:
    """Return full movie detail for the given TMDB ID. Returns 404 if not found."""
    return await service.get_movie(tmdb_id)
