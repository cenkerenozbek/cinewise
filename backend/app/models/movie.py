"""Pydantic models for movie-related API response bodies."""
from pydantic import BaseModel


class MovieSummary(BaseModel):
    """Core movie fields returned in list/search results."""

    tmdb_id: int
    title: str
    title_tr: str | None = None
    year: int | None = None
    genres: list[str] = []
    poster_path: str | None = None
    backdrop_path: str | None = None
    rating: float | None = None


class MovieDetail(MovieSummary):
    """Full movie fields including plot, crew, and cast — returned for /movies/{id}."""

    overview: str | None = None
    vote_count: int | None = None
    popularity: float | None = None
    director: str | None = None
    cast: list[str] = []


class MovieListResponse(BaseModel):
    """Paginated response envelope for movie list/search endpoints."""

    movies: list[MovieSummary]
    total: int
    page: int
    page_size: int


class GenresResponse(BaseModel):
    """Response envelope for the distinct genres endpoint."""

    genres: list[str]
