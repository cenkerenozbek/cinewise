"""Tests for offline evaluation pipeline functions — Phase 4."""
from datetime import datetime, timezone

import pytest

from jobs.evaluate import build_leave_one_out_test_set, compute_ndcg_at_k, precision_at_k


# ---------------------------------------------------------------------------
# precision_at_k tests
# ---------------------------------------------------------------------------


def test_precision_at_k_hit():
    """Returns 1.0 when relevant_id is in top-K of recommended list."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert precision_at_k(recommended, relevant_id=3) == 1.0


def test_precision_at_k_miss():
    """Returns 0.0 when relevant_id is NOT in top-K."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert precision_at_k(recommended, relevant_id=99) == 0.0


def test_precision_at_k_respects_k_boundary():
    """Item at exactly position K is included; item beyond K is excluded."""
    recommended = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert precision_at_k(recommended, relevant_id=10, k=10) == 1.0
    assert precision_at_k(recommended, relevant_id=11, k=10) == 0.0


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
