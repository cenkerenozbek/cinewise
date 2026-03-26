---
phase: 03-collaborative-filtering-and-hybrid-engine
plan: 01
subsystem: backend
tags: [feedback-api, rate-limiting, interactions, slowapi, tdd]
dependency_graph:
  requires: []
  provides: [POST /api/feedback, InteractionsRepository, slowapi limiter, CF artifact stubs]
  affects: [backend/app/main.py, backend/app/api/routes/recommendations.py]
tech_stack:
  added: [slowapi==0.1.9]
  patterns: [upsert-interactions, jwt-aware-rate-key, slowapi-with-response-param]
key_files:
  created:
    - backend/app/core/limiter.py
    - backend/app/repositories/interactions_repo.py
    - backend/app/api/routes/feedback.py
    - backend/tests/test_feedback.py
    - backend/tests/test_rate_limit.py
    - backend/tests/test_concurrency.py
  modified:
    - shared/config.py
    - backend/requirements.txt
    - backend/app/main.py
    - backend/app/api/routes/recommendations.py
    - backend/tests/conftest.py
decisions:
  - "slowapi headers_enabled=True required for Retry-After header injection"
  - "response: Response parameter required in get_recommendations for slowapi header injection into Pydantic-model responses"
  - "CF artifact stubs (cf_top_indices=None, cf_tmdb_ids=[]) added to main.py lifespan — Plan 03-03 will produce cf_index.joblib"
metrics:
  duration: 4 min
  completed: "2026-03-26"
  tasks_completed: 1
  files_changed: 11
---

# Phase 3 Plan 1: Feedback API, Rate Limiting, and Concurrency Summary

**One-liner:** POST /api/feedback with JWT auth + MongoDB upsert, slowapi rate limiting (10/min per user with Retry-After), and 10-concurrent-request smoke test — all 34 tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Interactions repo, feedback router, limiter module, config updates | dfcdde5 | 11 files |

## What Was Built

### POST /api/feedback Endpoint

- Authenticated users can submit `like` or `dislike` for any `movie_id`
- Upsert semantics: same `(user_id, movie_id)` pair replaces previous action
- 401 for missing/invalid JWT, 422 for invalid action values
- Returns 204 No Content on success

### InteractionsRepository

- Follows `UserPreferencesRepository` pattern exactly
- `upsert(user_id, movie_id, action)` — MongoDB `$set` + `upsert=True`
- `get_by_user_id(user_id)` — returns all interactions for a user
- `count_by_user_id(user_id)` — count for assertions in tests

### Rate Limiting (slowapi)

- `Limiter` singleton in `backend/app/core/limiter.py` to avoid circular imports
- Key function: `user:<user_id>` from JWT Bearer token, falls back to IP
- `@limiter.limit("10/minute")` on `POST /api/recommendations`
- `headers_enabled=True` ensures `Retry-After` header is included in 429 responses
- `response: Response` parameter added to `get_recommendations` for slowapi header injection

### MongoDB Indexes

- `(user_id, movie_id)` unique compound index on interactions collection
- `(user_id,)` index for efficient per-user queries

### CF Artifact Stubs

- `app.state.cf_top_indices = None` and `app.state.cf_tmdb_ids = []` stubs added to lifespan
- Plan 03-03 will produce `cf_index.joblib` that populates these at startup

## Test Coverage

| File | Tests | Result |
|------|-------|--------|
| test_feedback.py | 6 | PASS |
| test_rate_limit.py | 2 | PASS |
| test_concurrency.py | 1 | PASS |
| Full suite (34 tests) | 34 | PASS — no regressions |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] slowapi installed in wrong Python environment**
- **Found during:** Task 1, initial test run
- **Issue:** The backend uses `/opt/homebrew/Caskroom/miniforge/base/bin/python` (conda), not the system Python. `pip install slowapi` went to the system pip instead.
- **Fix:** Used `/opt/homebrew/Caskroom/miniforge/base/bin/pip install slowapi==0.1.9`
- **Files modified:** None (environment fix)
- **Commit:** dfcdde5

**2. [Rule 1 - Bug] slowapi Retry-After header not emitted with default config**
- **Found during:** Task 1, test_rate_limit_includes_retry_after failure
- **Issue:** `Limiter` defaults to `headers_enabled=False`, so no rate limit headers are injected into responses.
- **Fix:** Added `headers_enabled=True` to `Limiter(...)` constructor in `limiter.py`
- **Files modified:** `backend/app/core/limiter.py`
- **Commit:** dfcdde5

**3. [Rule 1 - Bug] slowapi _inject_headers receives None for Pydantic-model endpoints**
- **Found during:** Task 1, after enabling headers_enabled=True
- **Issue:** When the endpoint returns a Pydantic model (not a `Response`), slowapi's `async_wrapper` calls `kwargs.get("response")` to find the response object for header injection. Without a `response: Response` kwarg, it gets `None`, causing `Exception: parameter response must be an instance of starlette.responses.Response`.
- **Fix:** Added `response: Response` as a parameter to `get_recommendations` — FastAPI injects a mutable `Response` object that slowapi can mutate for header injection.
- **Files modified:** `backend/app/api/routes/recommendations.py`
- **Commit:** dfcdde5

## Decisions Made

1. **slowapi `headers_enabled=True`** — Required to include `Retry-After` and `X-RateLimit-*` headers in rate-limited responses. This is the standard behavior users expect from rate limiting.

2. **`response: Response` in `get_recommendations`** — FastAPI's `Response` parameter injection pattern lets slowapi inject headers into the response without changing the return type from the Pydantic model. This is the idiomatic FastAPI pattern for header manipulation.

3. **CF artifact stubs** — Added `cf_top_indices=None` and `cf_tmdb_ids=[]` to main.py lifespan and both test fixtures so Plan 03-03 can set these without any main.py changes needed.

## Self-Check: PASSED

Files created:
- FOUND: backend/app/core/limiter.py
- FOUND: backend/app/repositories/interactions_repo.py
- FOUND: backend/app/api/routes/feedback.py
- FOUND: backend/tests/test_feedback.py
- FOUND: backend/tests/test_rate_limit.py
- FOUND: backend/tests/test_concurrency.py

Commit verified: dfcdde5
