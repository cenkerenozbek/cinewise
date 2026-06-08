"""Business logic for content-based movie recommendations."""
import logging
import math

import numpy as np
from fastapi import HTTPException

from app.core.config import settings
from app.models.recommendation import RecommendationItem, RecommendationResponse
from app.repositories.interactions_repo import InteractionsRepository
from app.repositories.user_preferences_repo import UserPreferencesRepository

logger = logging.getLogger("uvicorn.error")


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

    Likes boost matching candidates similar to the liked item. Dislikes penalize
    matching candidates similar to the disliked item. Feedback should rerank the
    current preference context, not introduce movies from unrelated genres.
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
            if neighbor_id in candidate_scores:
                sim = float(top_scores[liked_idx][j]) if top_scores is not None else 1.0
                candidate_scores[neighbor_id] += feedback_weight * sim

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
    "Tense": ["Thriller", "Horror", "Crime"],
    "Romantic": ["Romance", "Drama"],
    "Happy": ["Comedy", "Animation", "Family"],
    "Relaxing": ["Documentary", "Drama", "Music"],
    "Mind-bending": ["Science Fiction", "Mystery", "Fantasy"],
}
MOOD_BOOST = 1.6
SELECTED_GENRE_BOOST = 2.0
NON_MATCHING_GENRE_PENALTY = 0.25
MIN_RECOMMENDATION_VOTE_COUNT = 50
LOW_QUALITY_PENALTY = 0.1
UNSAFE_TITLE_TERMS = (
    "adult",
    "erotic",
    "porn",
    "x-rated",
)
TOP_K = 10
# Max genre-seed movies: only use high-quality films as seeds to reduce noise
_SEED_LIMIT = 300
_SEED_MIN_VOTES = 50
_GENRE_MATCH_BOOST = 0.55
_MOOD_MATCH_BOOST = 0.25
_HISTORY_SIGNAL_WEIGHT = 0.45


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


def _normalised_movie_embeddings(movie_embeddings, expected_rows: int) -> np.ndarray | None:
    """Return a safe, L2-normalised movie embedding matrix when available."""
    if movie_embeddings is None:
        return None
    embeddings = np.asarray(movie_embeddings, dtype=np.float32)
    if embeddings.ndim != 2 or embeddings.shape[0] != expected_rows:
        logger.warning(
            "Ignoring movie_embeddings artifact with shape %s for %s tmdb ids",
            getattr(embeddings, "shape", None),
            expected_rows,
        )
        return None
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return embeddings / norms


def _quality_weight(doc: dict) -> float:
    """Small tie-breaker weight so better-rated seed movies shape the query a bit more."""
    rating = doc.get("rating")
    if not isinstance(rating, int | float):
        return 1.0
    return 1.0 + max(0.0, min((float(rating) - 6.0) / 10.0, 0.25))


def _ranking_quality_boost(doc: dict) -> float:
    """Small ranking boost for stronger catalogue signals within the active genre pool."""
    rating = doc.get("rating")
    vote_count = doc.get("vote_count") or 0

    rating_boost = 0.0
    if isinstance(rating, int | float) and rating > 0:
        rating_boost = max(0.0, min((float(rating) - 5.5) / 10.0, 0.18))

    vote_boost = 0.0
    if isinstance(vote_count, int | float) and vote_count > 0:
        vote_boost = min(math.log1p(float(vote_count)) / math.log1p(10000.0), 1.0) * 0.12

    return rating_boost + vote_boost


def _build_preference_vector(
    docs: list[dict],
    genres: list[str],
    mood: str | None,
    id_to_idx: dict[int, int],
    movie_embeddings: np.ndarray,
) -> np.ndarray | None:
    """Build a runtime preference embedding from selected genres and mood."""
    selected_genres = set(genres)
    mood_genres = set(MOOD_GENRE_MAP.get(mood, [])) if mood else set()
    query = np.zeros(movie_embeddings.shape[1], dtype=np.float32)
    total_weight = 0.0

    for doc in docs:
        idx = id_to_idx.get(doc.get("tmdb_id"))
        if idx is None:
            continue
        doc_genres = set(doc.get("genres", []))
        genre_matches = len(doc_genres & selected_genres)
        mood_matches = len(doc_genres & mood_genres)
        weight = float(genre_matches) + 0.75 * float(mood_matches)
        if weight <= 0.0:
            continue
        weight *= _quality_weight(doc)
        query += movie_embeddings[idx] * weight
        total_weight += weight

    if total_weight <= 0.0:
        return None

    query /= total_weight
    norm = float(np.linalg.norm(query))
    if norm <= 0.0:
        return None
    return query / norm


def _score_with_preference_embedding(
    query_docs: list[dict],
    candidate_docs: list[dict],
    genres: list[str],
    mood: str | None,
    id_to_idx: dict[int, int],
    movie_embeddings: np.ndarray,
) -> dict[int, float]:
    """Score candidate movies against the current genre/mood preference vector."""
    query = _build_preference_vector(query_docs, genres, mood, id_to_idx, movie_embeddings)
    if query is None:
        return {}

    selected_genres = set(genres)
    mood_genres = set(MOOD_GENRE_MAP.get(mood, [])) if mood else set()
    semantic_scores = movie_embeddings @ query
    candidate_scores: dict[int, float] = {}

    for doc in candidate_docs:
        tmdb_id = doc.get("tmdb_id")
        idx = id_to_idx.get(tmdb_id)
        if idx is None:
            continue

        doc_genres = set(doc.get("genres", []))
        genre_matches = len(doc_genres & selected_genres)
        mood_matches = len(doc_genres & mood_genres)
        score = float(semantic_scores[idx])
        score += _GENRE_MATCH_BOOST * min(genre_matches, 3)
        score += _MOOD_MATCH_BOOST * min(mood_matches, 2)
        score += _ranking_quality_boost(doc)

        candidate_scores[int(tmdb_id)] = score

    return candidate_scores


def _apply_preference_genre_guard(
    candidate_scores: dict[int, float],
    candidate_docs: list[dict],
    selected_genres: list[str],
    top_k: int = TOP_K,
) -> None:
    """Keep cold-start recommendations anchored to the user's selected genres.

    Similarity neighbors can include broadly related movies that do not actually
    match the selected genre. If enough genre-matching candidates exist, remove
    non-matching candidates. Otherwise, boost matches and penalize non-matches so
    sparse test/demo data can still return a full list.
    """
    selected = set(selected_genres)
    if not selected or not candidate_scores:
        return

    matching_ids = {
        doc["tmdb_id"]
        for doc in candidate_docs
        if set(doc.get("genres", [])) & selected
    }

    if len(matching_ids) >= top_k:
        for tmdb_id in list(candidate_scores):
            if tmdb_id not in matching_ids:
                candidate_scores.pop(tmdb_id, None)
        return

    for tmdb_id in list(candidate_scores):
        if tmdb_id in matching_ids:
            candidate_scores[tmdb_id] *= SELECTED_GENRE_BOOST
        else:
            candidate_scores[tmdb_id] *= NON_MATCHING_GENRE_PENALTY


def _is_recommendable_quality(doc: dict) -> bool:
    """Return whether a movie has enough public signal for demo-safe ranking."""
    if doc.get("adult") is True:
        return False
    title = (doc.get("title") or "").casefold()
    if any(term in title for term in UNSAFE_TITLE_TERMS):
        return False
    rating = doc.get("rating")
    vote_count = doc.get("vote_count")
    if rating is not None and rating <= 0:
        return False
    if vote_count is not None and vote_count < MIN_RECOMMENDATION_VOTE_COUNT:
        return False
    return True


def _apply_recommendable_quality_filter(
    candidate_scores: dict[int, float],
    candidate_docs: list[dict],
    top_k: int = TOP_K,
) -> None:
    """Prefer movies with enough vote signal; keep sparse fixtures usable."""
    if not candidate_scores:
        return

    recommendable_ids = {
        doc["tmdb_id"]
        for doc in candidate_docs
        if _is_recommendable_quality(doc)
    }

    if len(recommendable_ids) >= top_k:
        for tmdb_id in list(candidate_scores):
            if tmdb_id not in recommendable_ids:
                candidate_scores.pop(tmdb_id, None)
        return

    for tmdb_id in list(candidate_scores):
        if tmdb_id not in recommendable_ids:
            candidate_scores[tmdb_id] *= LOW_QUALITY_PENALTY


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
        tmdb_ids = list(getattr(self._state, "tmdb_ids", []))
        top_indices = getattr(self._state, "top_indices", None)
        top_scores = getattr(self._state, "top_scores", None)
        movie_embeddings = _normalised_movie_embeddings(
            getattr(self._state, "movie_embeddings", None),
            len(tmdb_ids),
        )
        if top_indices is None and movie_embeddings is None:
            raise HTTPException(503, "Recommendation engine not ready — run NLP pipeline first")

        if user_id:
            await self._prefs_repo.upsert(user_id, genres, mood)

        id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}

        catalog_cursor = self._db.movies.find(
            {"tmdb_id": {"$in": tmdb_ids}},
            {"tmdb_id": 1, "genres": 1, "rating": 1, "vote_count": 1},
        )
        catalog_docs = await catalog_cursor.to_list(length=None)

        # Find seed movies matching user's genre preferences.
        # Prefer popular films (vote_count threshold) to reduce noise; fall back
        # to all genre matches if the filtered result set is too small.
        selected_genres = set(genres)
        matching_docs = [
            doc for doc in catalog_docs if set(doc.get("genres", [])) & selected_genres
        ]
        popular_matches = [
            doc for doc in matching_docs if (doc.get("vote_count") or 0) >= _SEED_MIN_VOTES
        ]
        seed_source = popular_matches if len(popular_matches) >= 10 else matching_docs
        genre_docs = sorted(
            seed_source,
            key=lambda d: (
                d.get("rating") if isinstance(d.get("rating"), int | float) else 0.0,
                d.get("vote_count") or 0,
            ),
            reverse=True,
        )[:_SEED_LIMIT]
        # Explicit genre/mood selections define the candidate pool. Profile and
        # feedback signals may rerank this pool, but should not pull the list
        # away from the user's current genre intent. Tiny catalogues/tests fall
        # back to the whole catalogue so the API can still fill a top-10 list.
        candidate_docs = matching_docs if len(matching_docs) >= TOP_K else catalog_docs
        allowed_candidate_ids = {int(doc["tmdb_id"]) for doc in candidate_docs}

        if not catalog_docs:
            logger.warning("No catalogue docs match NLP artifact ids — falling back to top-rated")
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

        candidate_scores: dict[int, float] = {}
        if movie_embeddings is not None:
            candidate_scores = _score_with_preference_embedding(
                genre_docs,
                candidate_docs,
                genres,
                mood,
                id_to_idx,
                movie_embeddings,
            )

        # Backward-compatible path for old artifacts that do not include embeddings.
        if not candidate_scores and top_indices is not None:
            for doc in genre_docs:
                idx = id_to_idx.get(doc["tmdb_id"])
                if idx is None:
                    continue
                for j, neighbor_idx in enumerate(top_indices[idx]):
                    neighbor_id = tmdb_ids[int(neighbor_idx)]
                    if neighbor_id not in allowed_candidate_ids:
                        continue
                    sim = float(top_scores[idx][j]) if top_scores is not None else 1.0
                    candidate_scores[neighbor_id] = candidate_scores.get(neighbor_id, 0.0) + sim

        candidate_ids = list(candidate_scores.keys())
        candidate_docs = []
        if candidate_ids:
            cand_cursor = self._db.movies.find(
                {"tmdb_id": {"$in": candidate_ids}},
                {"tmdb_id": 1, "title": 1, "genres": 1, "rating": 1, "vote_count": 1, "adult": 1},
            )
            candidate_docs = await cand_cursor.to_list(length=None)

        _apply_preference_genre_guard(candidate_scores, candidate_docs, genres)
        _apply_recommendable_quality_filter(candidate_scores, candidate_docs)

        # Apply mood boost after the selected genre guard so mood refines the
        # preference instead of replacing it with broad genres like Drama.
        if mood and mood in MOOD_GENRE_MAP:
            boost_genres = set(MOOD_GENRE_MAP[mood])
            for cdoc in candidate_docs:
                tmdb_id = cdoc["tmdb_id"]
                if tmdb_id in candidate_scores and set(cdoc.get("genres", [])) & boost_genres:
                    candidate_scores[tmdb_id] *= MOOD_BOOST

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

            # History reranks the active genre/mood pool; it must not dominate
            # the current explicit request or make recommendations feel fixed.
            history_weight = _HISTORY_SIGNAL_WEIGHT
            if top_indices is not None:
                history_scores: dict[int, float] = {}
                for liked_id in liked_movie_ids:
                    liked_idx = id_to_idx.get(liked_id)
                    if liked_idx is None:
                        continue
                    completion = completion_map.get(liked_id)
                    weight = history_weight * _get_completion_weight(completion)
                    if weight <= 0:
                        continue
                    for j, neighbor_idx in enumerate(top_indices[liked_idx]):
                        neighbor_id = tmdb_ids[int(neighbor_idx)]
                        if neighbor_id not in candidate_scores:
                            continue
                        sim = float(top_scores[liked_idx][j]) if top_scores is not None else 1.0
                        history_scores[neighbor_id] = (
                            history_scores.get(neighbor_id, 0.0) + weight * sim
                        )

                for disliked_id in disliked_movie_ids:
                    disliked_idx = id_to_idx.get(disliked_id)
                    if disliked_idx is None:
                        continue
                    for j, neighbor_idx in enumerate(top_indices[disliked_idx]):
                        neighbor_id = tmdb_ids[int(neighbor_idx)]
                        if neighbor_id in candidate_scores:
                            sim = (
                                float(top_scores[disliked_idx][j])
                                if top_scores is not None
                                else 1.0
                            )
                            history_scores[neighbor_id] = (
                                history_scores.get(neighbor_id, 0.0) - history_weight * sim
                            )

                max_history = max((abs(v) for v in history_scores.values()), default=0.0)
                if max_history > 0:
                    for neighbor_id, score in history_scores.items():
                        candidate_scores[neighbor_id] += _HISTORY_SIGNAL_WEIGHT * (
                            score / max_history
                        )

            if getattr(self._state, "cf_top_indices", None) is not None:
                alpha = _get_alpha(
                    len(user_interactions), settings.CF_THRESHOLD, settings.CF_ALPHA
                )

        if alpha < 1.0 and getattr(self._state, "cf_top_indices", None) is not None:
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
        logger.info(
            "recommendations genres=%s mood=%s user=%s candidates=%s interactions=%s top_ids=%s",
            genres,
            mood,
            "auth" if user_id else "anonymous",
            len(candidate_scores),
            len(user_interactions),
            top_ids,
        )

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
