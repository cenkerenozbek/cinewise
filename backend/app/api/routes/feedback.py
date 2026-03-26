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

    @field_validator("action")
    @classmethod
    def action_must_be_binary(cls, v: str) -> str:
        if v not in ("like", "dislike"):
            raise ValueError("action must be 'like' or 'dislike'")
        return v


@router.post("", status_code=204)
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    """Persist like/dislike feedback for a movie.

    Authenticated users only. Submitting feedback for the same movie replaces
    the previous action (upsert semantics). Returns 204 No Content on success.
    """
    repo = InteractionsRepository(db)
    await repo.upsert(user_id, body.movie_id, body.action)
