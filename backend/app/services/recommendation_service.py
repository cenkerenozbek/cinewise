"""Business logic for content-based movie recommendations."""
import logging
from fastapi import HTTPException

from app.core.config import settings
from app.models.recommendation import RecommendationItem, RecommendationResponse
from app.repositories.interactions_repo import InteractionsRepository
from app.repositories.user_preferences_repo import UserPreferencesRepository

logger = logging.getLogger(__name__)


def _norm(scores: dict) -> dict:
    """Min-max normalize a score dict to [0, 1].

    Edge case: if max == min (all scores identical), return 0.5 for all.
    """
    if not scores:
        return scores
    min_s = min(scores.values())
    max_s = max(scores.values())
    if max_s == min_s:
        return {k: 0.5 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


def _get_alpha(interaction_count: int, threshold: int, cf_alpha: float) -> float:
    """Step function: pure content below threshold, blend at/above threshold."""
    if interaction_count >= threshold:
        return cf_alpha
    return 1.0

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

        # --- Hybrid blending (Phase 3) ---
        # Determine alpha based on user's interaction count
        alpha = 1.0  # default: pure content
        if user_id and self._state.cf_top_indices is not None:
            interactions_repo = InteractionsRepository(self._db)
            interaction_count = await interactions_repo.count_by_user_id(user_id)
            alpha = _get_alpha(interaction_count, settings.CF_THRESHOLD, settings.CF_ALPHA)

        if alpha < 1.0 and self._state.cf_top_indices is not None:
            # Build CF scores for candidates
            cf_tmdb_ids = self._state.cf_tmdb_ids
            cf_top_indices = self._state.cf_top_indices
            cf_id_to_idx = {tid: i for i, tid in enumerate(cf_tmdb_ids)}

            # Get user's liked movies from interactions
            user_interactions = await interactions_repo.get_by_user_id(user_id)
            liked_movie_ids = [ia["movie_id"] for ia in user_interactions if ia["action"] == "like"]

            # Score candidates by CF: how often they appear as CF neighbors of liked movies
            cf_scores: dict = {}
            for liked_id in liked_movie_ids:
                liked_idx = cf_id_to_idx.get(liked_id)
                if liked_idx is None:
                    continue
                for neighbor_idx in cf_top_indices[liked_idx]:
                    neighbor_id = cf_tmdb_ids[int(neighbor_idx)]
                    if neighbor_id in candidate_scores:  # only score existing candidates
                        cf_scores[neighbor_id] = cf_scores.get(neighbor_id, 0.0) + 1.0

            # Normalize and blend
            if cf_scores:
                norm_content = _norm(candidate_scores)
                norm_cf = _norm(cf_scores)
                for tid in candidate_scores:
                    content_val = norm_content.get(tid, 0.0)
                    cf_val = norm_cf.get(tid, 0.0)
                    candidate_scores[tid] = alpha * content_val + (1.0 - alpha) * cf_val
        # --- End hybrid blending ---

        # Rank and take top-K
        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)[:TOP_K]

        # Fetch full movie documents
        if not top_ids:
            return RecommendationResponse(recommendations=[])

        docs = await self._db.movies.find({"tmdb_id": {"$in": top_ids}}).to_list(length=None)

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
