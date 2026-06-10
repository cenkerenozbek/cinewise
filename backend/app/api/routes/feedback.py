"""FastAPI router for feedback endpoints.

Endpoints:
- POST /api/feedback — Submit like or dislike feedback for a movie (authenticated)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.interactions_repo import InteractionsRepository

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    movie_id: int
    action: str
    watch_completion: float | None = None

    @field_validator("action")
    @classmethod
    def action_must_be_binary(cls, v: str) -> str:
        if v not in ("like", "dislike"):
            raise ValueError("action must be 'like' or 'dislike'")
        return v

    @field_validator("watch_completion")
    @classmethod
    def completion_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("watch_completion must be between 0.0 and 1.0")
        return v


@router.get("/{movie_id}")
async def get_feedback(
    movie_id: int,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Return the user's existing feedback for a movie, or empty object if none."""
    repo = InteractionsRepository(db)
    doc = await repo.get_by_user_and_movie(user_id, movie_id)
    if not doc:
        return {}
    return {
        "action": doc.get("action"),
        "watch_completion": doc.get("watch_completion"),
    }


@router.post("", status_code=204)
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    """Persist like/dislike feedback for a movie.

    Authenticated users only. Submitting feedback for the same movie replaces
    the previous action (upsert semantics). Returns 204 No Content on success.
    Optional watch_completion (0.0–1.0) stores how much of the movie was watched.
    """
    repo = InteractionsRepository(db)
    await repo.upsert(user_id, body.movie_id, body.action, body.watch_completion)


@router.delete("/{movie_id}", status_code=204)
async def delete_feedback(
    movie_id: int,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    """Remove a user's feedback for a specific movie."""
    repo = InteractionsRepository(db)
    await repo.delete(user_id, movie_id)
