---
phase: 04-evaluation-and-demo-preparation
plan: "02"
subsystem: worker
tags: [evaluation, metrics, offline-eval, demo, uat, precision, ndcg, leave-one-out]
dependency_graph:
  requires:
    - worker/jobs/cf_features.py
    - worker/jobs/seed_interactions.py
    - backend/app/services/recommendation_service.py
  provides:
    - worker/jobs/evaluate.py
    - worker/jobs/reset_demo.py
    - worker/tests/test_eval_pipeline.py
  affects:
    - artifacts/metrics.json (runtime output)
tech_stack:
  added: []
  patterns:
    - sklearn ndcg_score with binary relevance labels for NDCG@K computation
    - Leave-one-out evaluation split sorted by updated_at ascending
    - EvalState adapter mimicking FastAPI app.state for offline service usage
    - passlib bcrypt for demo account password hashing (matching backend auth)
    - Dry-run flag pattern for safe demo resets during live presentations
key_files:
  created:
    - worker/jobs/evaluate.py
    - worker/jobs/reset_demo.py
    - worker/tests/test_eval_pipeline.py
  modified: []
decisions:
  - Use seed_user_ namespace exclusively for eval population — real users excluded to avoid contaminating offline metrics
  - EvalState adapter instead of mocking app.state — simpler and more robust than monkeypatching lifespan state
  - Fallback to top-6 rated movies when fewer than 5 canonical TMDB IDs exist in the DB — makes reset_demo idempotent even on a minimal dataset
  - sklearn ndcg_score with shape (1, k) arrays — reuses existing scikit-learn dependency instead of custom log2 implementation
metrics:
  duration: "3 min"
  completed_date: "2026-03-26"
  tasks: 2
  files: 3
---

# Phase 4 Plan 02: Offline Evaluation and Demo Reset Summary

**One-liner:** Precision@10 and NDCG@10 leave-one-out evaluator writing metrics.json plus idempotent demo reset script with passlib bcrypt account creation and dry-run support.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for eval pipeline | 96c35b3 | worker/tests/test_eval_pipeline.py |
| 1 (GREEN) | evaluate.py with P@10 and NDCG@10 | 4814e70 | worker/jobs/evaluate.py |
| 2 | reset_demo.py demo state management | 9ec32e9 | worker/jobs/reset_demo.py |

## What Was Built

### evaluate.py

Offline evaluation script for recommendation quality measurement:

- `precision_at_k(recommended_ids, relevant_id, k=10)`: returns 1.0 if relevant_id in top-k, else 0.0
- `compute_ndcg_at_k(recommended_ids, relevant_id, k=10)`: uses sklearn.metrics.ndcg_score with binary y_true labels and descending rank scores; returns 0.0 if miss
- `build_leave_one_out_test_set(interactions, min_likes=5, max_users=500)`: groups by user, filters likes only, excludes users below min_likes threshold, holds out the most-recent like (sorted by updated_at), returns (user_id, held_out_id, training_ids) tuples capped at max_users
- `EvalState`: adapter class mimicking FastAPI app.state so RecommendationService works offline without HTTP
- `main()`: CLI with --max-users and --artifacts-dir; queries seed_user_* interactions only; derives top-2 genres per test user from training set; calls RecommendationService directly; writes metrics.json

### reset_demo.py

Idempotent demo state management script:

- `ensure_user_exists(db, email, password)`: finds or creates account with passlib bcrypt-hashed password
- `reset_demo(db, dry_run)`: ensures both accounts exist, clears all interactions, checks canonical TMDB IDs against movies collection, falls back to top-6 rated movies if fewer than 5 canonical movies are present, re-seeds canonical likes for demo_returning via upsert
- `cleanup_uat_accounts(db, uat_prefix, dry_run)`: deletes users, interactions, and preferences for accounts matching email prefix
- `main()`: argparse CLI with --uat-prefix and --dry-run flags

### test_eval_pipeline.py

10 unit tests covering all pure functions (no DB required):
- 3 precision_at_k tests (hit, miss, k-boundary)
- 3 compute_ndcg_at_k tests (rank ordering, miss, perfect score)
- 4 build_leave_one_out_test_set tests (threshold filter, held-out selection, max_users cap, dislike exclusion)

## Verification

```
34 passed in 5.52s
```

All 34 worker tests pass including 10 new eval pipeline tests. No regressions in cf_pipeline, nlp_pipeline, or pipeline test suites.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] worker/jobs/evaluate.py exists and contains all required symbols
- [x] worker/jobs/reset_demo.py exists and contains all required symbols
- [x] worker/tests/test_eval_pipeline.py exists with 10 tests
- [x] All 3 commits verified (96c35b3, 4814e70, 9ec32e9)
- [x] 34/34 worker tests pass
