"""Business logic for content-based movie recommendations."""
import logging
import math

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
    """Smooth sigmoid transition from pure content (1.0) to blended (cf_alpha).

    Replaces the old step function with a sigmoid centred at the threshold so
    CF influence grows gradually as the user accumulates interactions.
    Returns exactly 1.0 at zero interactions; converges toward cf_alpha as
    interaction_count grows large.
    """
    if interaction_count <= 0:
        return 1.0
    x = (interaction_count - threshold) / max(threshold / 2.0, 1.0)
    blend = 1.0 / (1.0 + math.exp(-x))
    return 1.0 - (1.0 - cf_alpha) * blend


def _apply_interaction_content_feedback(
    candidate_scores: dict[int, float],
    liked_movie_ids: list[int],
    disliked_movie_ids: list[int],
    tmdb_ids: list[int],
    top_indices,
    feedback_weight: float,
    top_scores=None,
) -> None:
    """Apply immediate content-neighbour feedback before CF threshold is reached.

    Likes boost movies similar to the liked item; dislikes penalise them.
    When top_scores are available, the adjustment is further weighted by the
    actual cosine similarity so that closer neighbours are affected more.
    """
    if not liked_movie_ids and not disliked_movie_ids:
        return

    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

    for liked_id in liked_movie_ids:
        liked_idx = id_to_idx.get(liked_id)
        if liked_idx is None:
            continue
        for j, neighbor_idx in enumerate(top_indices[liked_idx]):
            neighbor_id = tmdb_ids[int(neighbor_idx)]
            sim = float(top_scores[liked_idx][j]) if top_scores is not None else 1.0
            candidate_scores[neighbor_id] = (
                candidate_scores.get(neighbor_id, 0.0) + feedback_weight * sim
            )

    for disliked_id in disliked_movie_ids:
        disliked_idx = id_to_idx.get(disliked_id)
        if disliked_idx is None:
            continue
        for j, neighbor_idx in enumerate(top_indices[disliked_idx]):
            neighbor_id = tmdb_ids[int(neighbor_idx)]
            if neighbor_id in candidate_scores:
                sim = float(top_scores[disliked_idx][j]) if top_scores is not None else 1.0
                candidate_scores[neighbor_id] -= feedback_weight * sim


MOOD_GENRE_MAP = {
    "Tense": ["Thriller", "Horror"],
    "Romantic": ["Romance", "Drama"],
    "Happy": ["Comedy", "Animation"],
    "Relaxing": ["Documentary", "Drama"],
    "Mind-bending": ["Science Fiction", "Mystery"],
}
MOOD_BOOST = 1.3
TOP_K = 10


def _get_completion_weight(completion: float | None) -> float:
    """Map watch_completion (0.0–1.0) to a feedback weight multiplier.

    Higher completion = stronger signal that the user enjoyed the film.
    Barely watched = mild negative signal (different from dislike).
    """
    if completion is None:
        return 1.0
    if completion >= 0.9:
        return 1.5
    if completion >= 0.5:
        return 1.2
    if completion >= 0.1:
        return 1.0
    return -0.3


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

        if user_id:
            await self._prefs_repo.upsert(user_id, genres, mood)

        tmdb_ids = self._state.tmdb_ids
        top_indices = self._state.top_indices
        top_scores = getattr(self._state, "top_scores", None)
        id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

        # Find seed movies matching user's genre preferences
        cursor = self._db.movies.find(
            {"genres": {"$in": genres}},
            {"tmdb_id": 1, "genres": 1},
        )
        genre_docs = await cursor.to_list(length=None)

        # Cold-start fallback: no genre-matching movies → return top-rated
        if not genre_docs:
            logger.warning("No movies match genres %s — falling back to top-rated", genres)
            fallback_cursor = (
                self._db.movies.find({"rating": {"$ne": None}}).sort("rating", -1).limit(TOP_K)
            )
            fallback_docs = await fallback_cursor.to_list(length=None)
            explanation = build_explanation(genres, mood)
            return RecommendationResponse(
                recommendations=[
                    RecommendationItem(
                        tmdb_id=d["tmdb_id"],
                        title=d.get("title", ""),
                        title_tr=d.get("title_tr"),
                        year=d.get("year"),
                        genres=d.get("genres", []),
                        poster_path=d.get("poster_path"),
                        rating=d.get("rating"),
                        overview=d.get("overview"),
                        explanation=explanation,
                    )
                    for d in fallback_docs
                ]
            )

        # Score candidates using weighted cosine similarity accumulation
        candidate_scores: dict[int, float] = {}
        for doc in genre_docs:
            idx = id_to_idx.get(doc["tmdb_id"])
            if idx is None:
                continue
            for j, neighbor_idx in enumerate(top_indices[idx]):
                neighbor_id = tmdb_ids[int(neighbor_idx)]
                sim = float(top_scores[idx][j]) if top_scores is not None else 1.0
                candidate_scores[neighbor_id] = candidate_scores.get(neighbor_id, 0.0) + sim

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

        # --- Hybrid blending ---
        alpha = 1.0
        user_interactions: list = []
        liked_movie_ids: list[int] = []
        disliked_movie_ids: list[int] = []

        if user_id:
            interactions_repo = InteractionsRepository(self._db)
            user_interactions = await interactions_repo.get_by_user_id(user_id)
            liked_movie_ids = [ia["movie_id"] for ia in user_interactions if ia["action"] == "like"]
            disliked_movie_ids = [
                ia["movie_id"] for ia in user_interactions if ia["action"] == "dislike"
            ]

            # Build completion weight map from watch_completion values
            completion_map: dict[int, float | None] = {
                ia["movie_id"]: ia.get("watch_completion")
                for ia in user_interactions
                if ia.get("watch_completion") is not None
            }

            base_feedback_weight = max(5.0, min(30.0, len(genre_docs) / 20.0))
            id_to_idx_feedback = {tid: i for i, tid in enumerate(tmdb_ids)}

            # Apply per-movie completion-weighted content feedback
            for liked_id in liked_movie_ids:
                liked_idx = id_to_idx_feedback.get(liked_id)
                if liked_idx is None:
                    continue
                completion = completion_map.get(liked_id)
                weight = base_feedback_weight * _get_completion_weight(completion)
                if weight == 0:
                    continue
                for j, neighbor_idx in enumerate(top_indices[liked_idx]):
                    neighbor_id = tmdb_ids[int(neighbor_idx)]
                    sim = float(top_scores[liked_idx][j]) if top_scores is not None else 1.0
                    candidate_scores[neighbor_id] = (
                        candidate_scores.get(neighbor_id, 0.0) + weight * sim
                    )

            for disliked_id in disliked_movie_ids:
                disliked_idx = id_to_idx_feedback.get(disliked_id)
                if disliked_idx is None:
                    continue
                for j, neighbor_idx in enumerate(top_indices[disliked_idx]):
                    neighbor_id = tmdb_ids[int(neighbor_idx)]
                    if neighbor_id in candidate_scores:
                        sim = float(top_scores[disliked_idx][j]) if top_scores is not None else 1.0
                        candidate_scores[neighbor_id] -= base_feedback_weight * sim

            if self._state.cf_top_indices is not None:
                alpha = _get_alpha(
                    len(user_interactions), settings.CF_THRESHOLD, settings.CF_ALPHA
                )

        if alpha < 1.0 and self._state.cf_top_indices is not None:
            cf_tmdb_ids = self._state.cf_tmdb_ids
            cf_top_indices = self._state.cf_top_indices
            cf_top_scores = getattr(self._state, "cf_top_scores", None)
            cf_id_to_idx = {tid: i for i, tid in enumerate(cf_tmdb_ids)}

            cf_scores: dict = {}
            for liked_id in liked_movie_ids:
                liked_idx = cf_id_to_idx.get(liked_id)
                if liked_idx is None:
                    continue
                for j, neighbor_idx in enumerate(cf_top_indices[liked_idx]):
                    neighbor_id = cf_tmdb_ids[int(neighbor_idx)]
                    if neighbor_id in candidate_scores:
                        sim = (
                            float(cf_top_scores[liked_idx][j])
                            if cf_top_scores is not None
                            else 1.0
                        )
                        cf_scores[neighbor_id] = cf_scores.get(neighbor_id, 0.0) + sim

            if cf_scores:
                norm_content = _norm(candidate_scores)
                norm_cf = _norm(cf_scores)
                for tid in candidate_scores:
                    candidate_scores[tid] = (
                        alpha * norm_content.get(tid, 0.0)
                        + (1.0 - alpha) * norm_cf.get(tid, 0.0)
                    )
        # --- End hybrid blending ---

        # Exclude already-seen movies
        if user_interactions:
            seen_ids = {ia["movie_id"] for ia in user_interactions}
            for mid in seen_ids:
                candidate_scores.pop(mid, None)

        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)[:TOP_K]

        if not top_ids:
            return RecommendationResponse(recommendations=[])

        docs = await self._db.movies.find({"tmdb_id": {"$in": top_ids}}).to_list(length=None)
        doc_map = {d["tmdb_id"]: d for d in docs}
        explanation = build_explanation(genres, mood)

        return RecommendationResponse(
            recommendations=[
                RecommendationItem(
                    tmdb_id=d["tmdb_id"],
                    title=d.get("title", ""),
                    title_tr=d.get("title_tr"),
                    year=d.get("year"),
                    genres=d.get("genres", []),
                    poster_path=d.get("poster_path"),
                    rating=d.get("rating"),
                    overview=d.get("overview"),
                    explanation=explanation,
                )
                for tid in top_ids
                if (d := doc_map.get(tid)) is not None
            ]
        )
