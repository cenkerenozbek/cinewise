"""Pydantic models for recommendation-related API request/response bodies."""
from pydantic import BaseModel, field_validator


class PreferenceRequest(BaseModel):
    """Request body for POST /api/recommendations."""

    genres: list[str]
    mood: str | None = None

    @field_validator("genres")
    @classmethod
    def genres_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one genre is required")
        return v

    @field_validator("mood")
    @classmethod
    def mood_valid(cls, v: str | None) -> str | None:
        valid_moods = {"Happy", "Tense", "Relaxing", "Mind-bending", "Romantic"}
        if v is not None and v not in valid_moods:
            raise ValueError(f"Mood must be one of: {', '.join(sorted(valid_moods))}")
        return v


class RecommendationItem(BaseModel):
    """A single movie recommendation with explanation."""

    tmdb_id: int
    title: str
    title_tr: str | None = None
    year: int | None = None
    genres: list[str] = []
    poster_path: str | None = None
    rating: float | None = None
    overview: str | None = None
    explanation: str


class RecommendationResponse(BaseModel):
    """Response body for POST /api/recommendations."""

    recommendations: list[RecommendationItem]


class UserPreferencesDoc(BaseModel):
    """Schema for the user_preferences MongoDB collection document."""

    user_id: str
    genres: list[str]
    mood: str | None = None
