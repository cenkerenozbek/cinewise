---
phase: 03-collaborative-filtering-and-hybrid-engine
plan: "02"
subsystem: worker
tags: [collaborative-filtering, batch-pipeline, seeding, movieLens, scipy, joblib]
dependency_graph:
  requires:
    - worker/jobs/nlp_features.py (similarity_index.joblib pattern)
    - shared/config.py (INTERACTIONS_COLLECTION)
    - MongoDB interactions collection
  provides:
    - worker/jobs/cf_features.py (CF batch pipeline)
    - worker/jobs/seed_interactions.py (MovieLens seeding)
    - cf_index.joblib artifact
  affects:
    - Plan 03-03 (hybrid blending reads cf_index.joblib)
tech_stack:
  added: [scipy.sparse.csr_matrix]
  patterns:
    - Sparse CSR matrix for user-item interactions (memory-efficient)
    - Row-by-row cosine_similarity loop (same as NLP pipeline)
    - joblib artifact serialization (consistent with NLP pipeline)
    - csv.DictReader for CSV parsing (no pandas dependency)
key_files:
  created:
    - worker/jobs/cf_features.py
    - worker/jobs/seed_interactions.py
    - worker/tests/test_cf_pipeline.py
  modified: []
decisions:
  - "[03-02] scipy.sparse.csr_matrix for user-item matrix — memory-safe for sparse interaction data"
  - "[03-02] csv.DictReader for MovieLens CSV parsing — avoids pandas dependency"
  - "[03-02] Canonical tmdb_ids sourced from similarity_index.joblib in cf_features main — ensures CF and NLP artifacts are aligned"
  - "[03-02] int(float(tmdb_raw)) parsing in links.csv — handles '12345.0' numeric format from MovieLens"
metrics:
  duration: "3 min"
  completed: "2026-03-26"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Phase 03 Plan 02: CF Batch Pipeline and MovieLens Seeding Summary

**One-liner:** Item-based CF batch pipeline using sparse CSR matrix and cosine similarity, plus MovieLens-20M seeding script mapping ratings to TMDB IDs with like/dislike thresholds.

## What Was Built

### Task 1: CF batch pipeline with unit tests (TDD)

`worker/jobs/cf_features.py`:
- `build_cf_index(interactions, tmdb_ids, top_n=50)` — builds sparse user-item CSR matrix (scipy), transposes to item-feature matrix, computes row-by-row cosine similarity with self-exclusion (`sims[i] = -1.0`), returns `np.ndarray` of shape `(N_movies, effective_top_n)` with `dtype=int32`
- `save_cf_artifacts(tmdb_ids, cf_top_indices, artifacts_dir)` — writes `cf_index.joblib` with `{"tmdb_ids": ..., "cf_top_indices": ...}`
- `async def main()` — loads canonical `tmdb_ids` from `similarity_index.joblib`, reads interactions from MongoDB, builds and saves CF artifact

`worker/tests/test_cf_pipeline.py` — 6 tests covering:
1. Shape `(N, min(top_n, N-1))` with `int32` dtype
2. Self-exclusion: movie index `i` absent from `cf_top_indices[i]`
3. Like/dislike scoring semantics with co-liked movies being neighbors
4. Empty interactions returns `(N, 0)` gracefully
5. Unknown `movie_id` silently skipped
6. `save_cf_artifacts` writes loadable `cf_index.joblib` with correct keys

### Task 2: MovieLens seeding script

`worker/jobs/seed_interactions.py`:
- `load_links_mapping(links_path)` — reads `links.csv`, handles `"12345.0"` format via `int(float(...))`, builds `ml_movie_id -> tmdb_id` dict
- `classify_rating(rating)` — `>= 4.0 -> "like"`, `<= 2.0 -> "dislike"`, ambiguous returns `None`
- `build_interactions(ratings_path, ml_to_tmdb, existing_tmdb_ids, seed_user_limit)` — filters to first `SEED_USER_LIMIT` unique users, only movies in DB, maps to `seed_user_{userId}` namespace
- `async def main()` — idempotent via `delete_many({"user_id": {"$regex": "^seed_user_"}})`, batch insert in 5000-doc chunks, logs stats

## Verification Results

```
worker $ pytest tests/ -x -q
........................
24 passed in 5.30s
```

- 6 new CF pipeline tests pass
- 18 existing tests pass (zero regressions)
- `python -c "from jobs.seed_interactions import main"` succeeds

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **scipy.sparse.csr_matrix for user-item matrix** — memory-safe for sparse interaction data; avoids dense N_users x N_movies matrix allocation
2. **csv.DictReader for CSV parsing** — avoids adding pandas as a dependency, consistent with keeping worker lightweight
3. **Canonical `tmdb_ids` from `similarity_index.joblib`** — ensures CF and NLP artifacts use identical movie ordering, critical for hybrid blending in Plan 03-03
4. **`int(float(tmdb_raw))` in links.csv parsing** — MovieLens ships `tmdbId` as float-formatted strings (`"12345.0"`); this handles it without error

## Self-Check: PASSED

| Item | Status |
|------|--------|
| worker/jobs/cf_features.py | FOUND |
| worker/jobs/seed_interactions.py | FOUND |
| worker/tests/test_cf_pipeline.py | FOUND |
| 03-02-SUMMARY.md | FOUND |
| Commit abf99b4 (RED tests) | FOUND |
| Commit 9f577da (GREEN impl) | FOUND |
| Commit 247864b (seed script) | FOUND |
