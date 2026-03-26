"""Business logic for content-based movie recommendations."""
import logging
from fastapi import HTTPException

from app.models.recommendation import RecommendationItem, RecommendationResponse
from app.repositories.user_preferences_repo import UserPreferencesRepository

logger = logging.getLogger(__name__)

MOOD_GENRE_MAP = {
    "Tense": ["Thriller", "Horror"],
    "Romantic": ["Romance", "Drama"],
    "Happy": ["Comedy", "Animation"],
    "Relaxing": ["Documentary", "Drama"],
    "Mind-bending": ["Science Fiction", "Mystery"],
}
MOOD_BOOST = 1.3
TOP_K = 10


def build_explanation(genres: list[str], mood: str | None) -> str:
    """Build human-readable explanation referencing user preferences."""
    if len(genres) == 1:
        genre_part = genres[0]
    else:
        genre_part = " and ".join(genres)
    if mood:
        return f"Recommended because you like {genre_part}, feeling {mood}."
    return f"Recommended because you like {genre_part}."


class RecommendationService:
    """Generates top-K recommendations using precomputed similarity index."""

    def __init__(self, db, app_state) -> None:
        self._db = db
        self._state = app_state
        self._prefs_repo = UserPreferencesRepository(db)

    async def get_recommendations(
        self,
        genres: list[str],
        mood: str | None,
        user_id: str | None = None,
    ) -> RecommendationResponse:
        if self._state.top_indices is None:
            raise HTTPException(503, "Recommendation engine not ready — run NLP pipeline first")

        # Save preferences if user is authenticated
        if user_id:
            await self._prefs_repo.upsert(user_id, genres, mood)

        tmdb_ids = self._state.tmdb_ids
        top_indices = self._state.top_indices
        id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

        # Find seed movies matching user's genre preferences
        cursor = self._db.movies.find(
            {"genres": {"$in": genres}},
            {"tmdb_id": 1, "genres": 1},
        )
        genre_docs = await cursor.to_list(length=None)

        # Score candidates by frequency in neighbors of genre-matching seeds
        candidate_scores: dict[int, float] = {}
        seed_tmdb_ids = set()
        for doc in genre_docs:
            idx = id_to_idx.get(doc["tmdb_id"])
            if idx is None:
                continue
            seed_tmdb_ids.add(doc["tmdb_id"])
            for neighbor_idx in top_indices[idx]:
                neighbor_id = tmdb_ids[int(neighbor_idx)]
                candidate_scores[neighbor_id] = candidate_scores.get(neighbor_id, 0.0) + 1.0

        # Remove seed movies from candidates (user already knows these genres)
        for sid in seed_tmdb_ids:
            candidate_scores.pop(sid, None)

        # Apply mood boost
        if mood and mood in MOOD_GENRE_MAP:
            boost_genres = set(MOOD_GENRE_MAP[mood])
            candidate_ids = list(candidate_scores.keys())
            if candidate_ids:
                cand_cursor = self._db.movies.find(
                    {"tmdb_id": {"$in": candidate_ids}},
                    {"tmdb_id": 1, "genres": 1},
                )
                cand_docs = await cand_cursor.to_list(length=None)
                for cdoc in cand_docs:
                    if set(cdoc.get("genres", [])) & boost_genres:
                        candidate_scores[cdoc["tmdb_id"]] *= MOOD_BOOST

        # Rank and take top-K
        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)[:TOP_K]

        # Fetch full movie documents
        if not top_ids:
            return RecommendationResponse(recommendations=[])

        docs = await self._db.movies.find({"tmdb_id": {"$in": top_ids}}).to_list(length=TOP_K)

        # Build response preserving score order
        doc_map = {d["tmdb_id"]: d for d in docs}
        explanation = build_explanation(genres, mood)
        recommendations = []
        for tid in top_ids:
            d = doc_map.get(tid)
            if d is None:
                continue
            recommendations.append(RecommendationItem(
                tmdb_id=d["tmdb_id"],
                title=d.get("title", ""),
                title_tr=d.get("title_tr"),
                year=d.get("year"),
                genres=d.get("genres", []),
                poster_path=d.get("poster_path"),
                rating=d.get("rating"),
                overview=d.get("overview"),
                explanation=explanation,
            ))

        return RecommendationResponse(recommendations=recommendations)
