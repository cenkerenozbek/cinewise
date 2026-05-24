"""Tests for offline evaluation pipeline functions — Phase 4."""
from datetime import datetime, timezone

import pytest

from jobs.evaluate import (
    build_leave_one_out_test_set,
    compute_mrr,
    compute_ndcg_at_k,
    hit_rate_at_k,
    precision_at_k,  # legacy alias — same function as hit_rate_at_k
    score_from_history,
)


# ---------------------------------------------------------------------------
# hit_rate_at_k tests  (HR@K = Recall@K with 1 relevant item)
# ---------------------------------------------------------------------------


def test_hit_rate_at_k_hit():
    """Returns 1.0 when relevant_id is in top-K of recommended list."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert hit_rate_at_k(recommended, relevant_id=3) == 1.0


def test_hit_rate_at_k_miss():
    """Returns 0.0 when relevant_id is NOT in top-K."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert hit_rate_at_k(recommended, relevant_id=99) == 0.0


def test_hit_rate_at_k_respects_k_boundary():
    """Item at exactly position K is included; item beyond K is excluded."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert hit_rate_at_k(recommended, relevant_id=10, k=10) == 1.0
    assert hit_rate_at_k(recommended, relevant_id=11, k=10) == 0.0


def test_precision_at_k_alias():
    """precision_at_k is a legacy alias for hit_rate_at_k — same behaviour."""
    assert precision_at_k([1, 2, 3], relevant_id=2) == hit_rate_at_k([1, 2, 3], relevant_id=2)


# ---------------------------------------------------------------------------
# compute_mrr tests
# ---------------------------------------------------------------------------


def test_mrr_rank1():
    """MRR = 1.0 when relevant item is at rank 1."""
    assert compute_mrr([42, 1, 2, 3], relevant_id=42) == pytest.approx(1.0)


def test_mrr_rank2():
    """MRR = 0.5 when relevant item is at rank 2."""
    assert compute_mrr([1, 42, 2, 3], relevant_id=42) == pytest.approx(0.5)


def test_mrr_miss():
    """MRR = 0.0 when relevant item is not in top-K."""
    assert compute_mrr([1, 2, 3], relevant_id=99) == 0.0


# ---------------------------------------------------------------------------
# compute_ndcg_at_k tests
# ---------------------------------------------------------------------------


def test_ndcg_at_k_rank1_beats_rank5():
    """Higher NDCG when relevant item is at rank 1 vs rank 5."""
    recs_rank1 = [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    recs_rank5 = [1, 2, 3, 4, 42, 5, 6, 7, 8, 9]
    assert compute_ndcg_at_k(recs_rank1, relevant_id=42) > compute_ndcg_at_k(recs_rank5, relevant_id=42)


def test_ndcg_at_k_miss():
    """Returns 0.0 when relevant_id is not in top-K."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert compute_ndcg_at_k(recommended, relevant_id=99) == 0.0


def test_ndcg_at_k_perfect_score():
    """Returns 1.0 when relevant item is at rank 1."""
    recommended = [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    score = compute_ndcg_at_k(recommended, relevant_id=42)
    assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# build_leave_one_out_test_set tests
# ---------------------------------------------------------------------------


def _make_interaction(user_id: str, movie_id: int, timestamp: int, action: str = "like") -> dict:
    """Helper to build an interaction dict with a deterministic updated_at."""
    return {
        "user_id": user_id,
        "movie_id": movie_id,
        "action": action,
        "updated_at": datetime.fromtimestamp(timestamp, tz=timezone.utc),
    }


# user_a: 6 likes with timestamps 1-6 — qualifies, held_out = movie 106 (ts=6)
# user_b: 3 likes — excluded (below min_likes=5)
# user_c: 5 likes with timestamps 10-14 — qualifies, held_out = movie 214 (ts=14)
SAMPLE_INTERACTIONS = [
    # user_a
    _make_interaction("user_a", 101, 1),
    _make_interaction("user_a", 102, 2),
    _make_interaction("user_a", 103, 3),
    _make_interaction("user_a", 104, 4),
    _make_interaction("user_a", 105, 5),
    _make_interaction("user_a", 106, 6),
    # user_b (only 3 likes — below threshold)
    _make_interaction("user_b", 201, 1),
    _make_interaction("user_b", 202, 2),
    _make_interaction("user_b", 203, 3),
    # user_c
    _make_interaction("user_c", 210, 10),
    _make_interaction("user_c", 211, 11),
    _make_interaction("user_c", 212, 12),
    _make_interaction("user_c", 213, 13),
    _make_interaction("user_c", 214, 14),
]


def test_leave_one_out_split_filters_below_threshold():
    """Users with fewer than min_likes likes are excluded from the test set."""
    result = build_leave_one_out_test_set(SAMPLE_INTERACTIONS, min_likes=5, max_users=500)
    user_ids = {entry[0] for entry in result}
    assert "user_b" not in user_ids
    assert len(result) == 2


def test_leave_one_out_split_holds_out_last():
    """Held-out item is the like with the highest updated_at timestamp."""
    result = build_leave_one_out_test_set(SAMPLE_INTERACTIONS, min_likes=5, max_users=500)
    result_map = {entry[0]: entry for entry in result}

    # user_a: held_out should be movie 106 (timestamp 6 is highest)
    _, held_out_a, training_a = result_map["user_a"]
    assert held_out_a == 106
    assert len(training_a) == 5  # 6 likes - 1 held out
    assert 106 not in training_a

    # user_c: held_out should be movie 214 (timestamp 14 is highest)
    _, held_out_c, training_c = result_map["user_c"]
    assert held_out_c == 214
    assert len(training_c) == 4  # 5 likes - 1 held out
    assert 214 not in training_c


def test_leave_one_out_split_respects_max_users():
    """Result length is capped at max_users."""
    result = build_leave_one_out_test_set(SAMPLE_INTERACTIONS, min_likes=5, max_users=1)
    assert len(result) == 1


def test_leave_one_out_split_no_timestamp_fallback():
    """Interactions without updated_at (seeded data pre-fix) fall back to insertion order 0."""
    # Build interactions without updated_at — simulate old seeded docs
    interactions_no_ts = [
        {"user_id": "user_e", "movie_id": 401, "action": "like"},
        {"user_id": "user_e", "movie_id": 402, "action": "like"},
        {"user_id": "user_e", "movie_id": 403, "action": "like"},
        {"user_id": "user_e", "movie_id": 404, "action": "like"},
        {"user_id": "user_e", "movie_id": 405, "action": "like"},
    ]
    # All sort keys resolve to 0, so stable sort preserves insertion order.
    # Held-out must be movie 405 (last in list after stable sort).
    result = build_leave_one_out_test_set(interactions_no_ts, min_likes=5, max_users=500)
    assert len(result) == 1
    _, held_out, training = result[0]
    assert held_out == 405
    assert len(training) == 4
    assert 405 not in training


def test_leave_one_out_split_excludes_dislikes():
    """Dislike interactions are not counted toward min_likes threshold."""
    interactions_with_dislikes = SAMPLE_INTERACTIONS + [
        _make_interaction("user_d", 301, 1, action="dislike"),
        _make_interaction("user_d", 302, 2, action="dislike"),
        _make_interaction("user_d", 303, 3, action="dislike"),
        _make_interaction("user_d", 304, 4, action="dislike"),
        _make_interaction("user_d", 305, 5, action="dislike"),
        _make_interaction("user_d", 306, 6, action="dislike"),
    ]
    result = build_leave_one_out_test_set(interactions_with_dislikes, min_likes=5, max_users=500)
    user_ids = {entry[0] for entry in result}
    assert "user_d" not in user_ids


# ---------------------------------------------------------------------------
# score_from_history tests
# ---------------------------------------------------------------------------


def _make_nlp_data(tmdb_ids: list[int], neighbors: dict[int, list[int]]) -> dict:
    """Build a minimal nlp_data dict for testing.

    neighbors maps tmdb_id -> list of neighbor tmdb_ids.
    """
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}
    top_indices = []
    for tid in tmdb_ids:
        neighbor_ids = neighbors.get(tid, [])
        top_indices.append([id_to_idx[n] for n in neighbor_ids if n in id_to_idx])
    import numpy as np
    return {"tmdb_ids": tmdb_ids, "top_indices": np.array(top_indices, dtype=object)}


def test_score_from_history_returns_candidates():
    """Neighbors of training movies appear in candidate scores.

    Without top_scores (old artifact format), frequency count is used:
    movie 4 is neighbor of both training movies so its score is doubled.
    """
    nlp = _make_nlp_data([1, 2, 3, 4, 5], {1: [3, 4], 2: [4, 5]})
    scores = score_from_history([1, 2], nlp, cf_data=None)
    assert set(scores.keys()) == {3, 4, 5}
    assert scores[4] > scores[3]  # movie 4 appears in both neighbourhoods


def test_score_from_history_uses_top_scores_when_available():
    """When top_scores are provided, weighted cosine sum is used instead of counts."""
    import numpy as np

    tmdb_ids = [1, 2, 3, 4, 5]
    id_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}
    # movie 1 → neighbors [3, 4]; movie 2 → neighbors [4, 5]
    top_indices = np.array(
        [[id_to_idx[3], id_to_idx[4]], [id_to_idx[4], id_to_idx[5]], [], [], []],
        dtype=object,
    )
    # Scores: 1→3 similarity=0.9, 1→4 similarity=0.1; 2→4 similarity=0.8, 2→5 similarity=0.5
    top_scores = np.array(
        [[0.9, 0.1], [0.8, 0.5], [], [], []],
        dtype=object,
    )
    nlp = {"tmdb_ids": tmdb_ids, "top_indices": top_indices, "top_scores": top_scores}
    scores = score_from_history([1, 2], nlp, cf_data=None)
    # movie 4: 0.1 (from 1) + 0.8 (from 2) = 0.9
    # movie 3: 0.9 (from 1 only)
    # movie 5: 0.5 (from 2 only)
    assert abs(scores[4] - 0.9) < 1e-5
    assert abs(scores[3] - 0.9) < 1e-5
    assert abs(scores[5] - 0.5) < 1e-5


def test_score_from_history_unknown_training_ids_ignored():
    """Training IDs not in the NLP index are silently skipped."""
    nlp = _make_nlp_data([1, 2, 3], {1: [2, 3]})
    scores = score_from_history([1, 999], nlp, cf_data=None)
    assert 2 in scores and 3 in scores  # from movie 1
    assert 999 not in scores


def test_score_from_history_empty_training_returns_empty():
    """Empty training list produces no candidates."""
    nlp = _make_nlp_data([1, 2, 3], {1: [2, 3]})
    scores = score_from_history([], nlp, cf_data=None)
    assert scores == {}


def test_score_from_history_history_limit_uses_last_n():
    """Applying a history limit uses only the last N training IDs."""
    # movie 1 → neighbors [10,11]; movie 2 → neighbors [20,21]
    nlp = _make_nlp_data([1, 2, 10, 11, 20, 21], {1: [10, 11], 2: [20, 21]})
    # full training [1, 2] → candidates include 10,11,20,21
    full = score_from_history([1, 2], nlp, cf_data=None)
    assert {10, 11, 20, 21}.issubset(full.keys())
    # limit to last 1 → only movie 2 used → only 20,21
    limited = score_from_history([1, 2][-1:], nlp, cf_data=None)
    assert 20 in limited and 21 in limited
    assert 10 not in limited and 11 not in limited
