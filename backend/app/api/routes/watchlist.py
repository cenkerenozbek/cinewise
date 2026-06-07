"""FastAPI router for watchlist endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.watchlist_repo import WatchlistRepository

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    movie_id: int


@router.get("")
async def get_watchlist(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Return the user's watchlist enriched with movie data."""
    repo = WatchlistRepository(db)
    entries = await repo.get_by_user_id(user_id)

    movie_ids = [e["movie_id"] for e in entries]
    if not movie_ids:
        return {"items": []}

    movie_cursor = db.movies.find(
        {"tmdb_id": {"$in": movie_ids}},
        {"tmdb_id": 1, "title": 1, "poster_path": 1, "genres": 1, "year": 1, "rating": 1},
    )
    movie_docs = await movie_cursor.to_list(length=None)
    movie_map = {doc["tmdb_id"]: doc for doc in movie_docs}

    items = []
    for entry in sorted(entries, key=lambda e: e.get("added_at", ""), reverse=True):
        movie = movie_map.get(entry["movie_id"], {})
        items.append({
            "movie_id": entry["movie_id"],
            "title": movie.get("title", "Unknown"),
            "poster_path": movie.get("poster_path"),
            "genres": movie.get("genres", []),
            "year": movie.get("year"),
            "rating": movie.get("rating"),
        })

    return {"items": items}


@router.post("", status_code=204)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    """Add a movie to the user's watchlist."""
    repo = WatchlistRepository(db)
    await repo.add(user_id, body.movie_id)


@router.delete("/{movie_id}", status_code=204)
async def remove_from_watchlist(
    movie_id: int,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    """Remove a movie from the user's watchlist."""
    repo = WatchlistRepository(db)
    await repo.remove(user_id, movie_id)
