"""FastAPI router for user history and profile stats endpoints."""
from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.interactions_repo import InteractionsRepository

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def get_history(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
    page: int = 1,
    filter: str = "all",
) -> dict:
    """Return paginated interaction history enriched with movie data."""
    repo = InteractionsRepository(db)
    interactions = await repo.get_by_user_id(user_id)

    # Apply filter
    if filter == "liked":
        interactions = [ia for ia in interactions if ia.get("action") == "like"]
    elif filter == "disliked":
        interactions = [ia for ia in interactions if ia.get("action") == "dislike"]
    elif filter == "watched":
        interactions = [ia for ia in interactions if ia.get("watch_completion") is not None]

    # Sort by most recent
    interactions.sort(key=lambda ia: ia.get("updated_at", ""), reverse=True)

    # Paginate
    page_size = 20
    total = len(interactions)
    start = (page - 1) * page_size
    page_interactions = interactions[start: start + page_size]

    # Enrich with movie data (two-query join — avoids $lookup for mongomock compat)
    movie_ids = [ia["movie_id"] for ia in page_interactions]
    movie_cursor = db.movies.find(
        {"tmdb_id": {"$in": movie_ids}},
        {"tmdb_id": 1, "title": 1, "poster_path": 1, "genres": 1, "year": 1, "rating": 1},
    )
    movie_docs = await movie_cursor.to_list(length=None)
    movie_map = {doc["tmdb_id"]: doc for doc in movie_docs}

    enriched = []
    for ia in page_interactions:
        movie = movie_map.get(ia["movie_id"], {})
        enriched.append({
            "movie_id": ia["movie_id"],
            "action": ia.get("action"),
            "watch_completion": ia.get("watch_completion"),
            "updated_at": ia.get("updated_at", "").isoformat() if hasattr(ia.get("updated_at", ""), "isoformat") else str(ia.get("updated_at", "")),
            "title": movie.get("title", "Unknown"),
            "poster_path": movie.get("poster_path"),
            "genres": movie.get("genres", []),
            "year": movie.get("year"),
            "rating": movie.get("rating"),
        })

    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/stats")
async def get_history_stats(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> dict:
    """Return aggregated stats and genre breakdown for a user's interactions."""
    repo = InteractionsRepository(db)
    base_stats = await repo.get_stats_by_user_id(user_id)
    interactions = await repo.get_by_user_id(user_id)

    # Compute genre counts from liked movies
    liked_ids = [ia["movie_id"] for ia in interactions if ia.get("action") == "like"]
    genre_counts: dict[str, int] = {}
    if liked_ids:
        movie_cursor = db.movies.find(
            {"tmdb_id": {"$in": liked_ids}},
            {"genres": 1},
        )
        movie_docs = await movie_cursor.to_list(length=None)
        for doc in movie_docs:
            for genre in doc.get("genres", []):
                genre_counts[genre] = genre_counts.get(genre, 0) + 1

    return {
        **base_stats,
        "genre_counts": genre_counts,
    }
