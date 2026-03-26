---
phase: 02-content-based-recommendation-engine
plan: 03
subsystem: api
tags: [fastapi, mongodb, numpy, joblib, recommendation, tfidf, pytest]

# Dependency graph
requires:
  - phase: 02-01
    provides: NLP artifacts (tfidf_vectorizer.joblib, similarity_index.joblib), PreferenceRequest/RecommendationItem/RecommendationResponse models, conftest fixtures with mock_nlp_state
  - phase: 01-foundation-and-data-pipeline
    provides: FastAPI app skeleton, auth/movies routers, UserRepository pattern, MovieRepository, get_db dependency, security/JWT utilities

provides:
  - POST /api/recommendations endpoint: accepts genres + optional mood, returns top-10 RecommendationItems with explanations
  - GET /api/recommendations/preferences: returns saved preferences for authenticated user
  - UserPreferencesRepository: CRUD for user_preferences MongoDB collection
  - RecommendationService: scores candidates via precomputed similarity index neighbors, applies 1.3x mood boost
  - build_explanation(): human-readable recommendation rationale ("Recommended because you like X and Y, feeling Z.")
  - NLP artifact loading at FastAPI startup via lifespan with graceful degradation

affects:
  - 02-04 (UI recommendation page uses this endpoint)
  - 03-collaborative-filtering (will add interaction tracking alongside preference persistence)

# Tech tracking
tech-stack:
  added: [joblib (NLP artifact loading at startup)]
  patterns: [TDD red-green for service + endpoint tests, optional JWT extraction without 401 for cold-start users, lifespan artifact loading with env-var path override]

key-files:
  created:
    - backend/app/repositories/user_preferences_repo.py
    - backend/app/services/recommendation_service.py
    - backend/app/api/routes/recommendations.py
  modified:
    - backend/app/main.py
    - backend/tests/conftest.py
    - backend/tests/test_recommendations.py

key-decisions:
  - "seed_movies fixture uses dict copies to prevent _id mutation across test runs in mongomock"
  - "client_with_nlp does not insert movies — seed_movies fixture owns insertion; shared test_db instance ensures both fixtures see same data"
  - "_get_optional_user returns None (not 401) for missing/invalid JWT — enables cold-start recommendations for unauthenticated users"
  - "Mood boost applied after neighbor scoring, not during — single additional query to fetch candidate genres; avoids per-candidate queries"

patterns-established:
  - "Optional auth pattern: _get_optional_user extracts sub from JWT without raising, returns None for anonymous users"
  - "Lifespan NLP loading: check file existence, load with joblib, set app.state fields; warn+degrade gracefully when artifacts absent"
  - "Recommendation scoring: seed by genre-matching movies -> aggregate neighbor votes -> remove seeds -> apply mood boost -> rank -> fetch full docs"

requirements-completed: [NLP-04, REC-01, REC-02, REC-05, API-02, API-05]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 02 Plan 03: Recommendation API Summary

**POST /api/recommendations serving precomputed TF-IDF similarity neighbors with 1.3x mood boost and genre-based explanations, loading joblib artifacts at FastAPI startup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T04:16:13Z
- **Completed:** 2026-03-26T04:19:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- UserPreferencesRepository with upsert/get for MongoDB user_preferences collection
- RecommendationService scoring pipeline: genre-matched seeds -> neighbor vote aggregation -> mood boost -> top-10 ranking
- POST /api/recommendations endpoint with optional JWT auth (cold-start safe) and explanation generation
- NLP artifacts loaded at FastAPI startup from ARTIFACTS_DIR via joblib; graceful 503 degradation when missing
- All 9 recommendation tests pass; all 25 backend tests pass (no regressions in auth/movies)

## Task Commits

Each task was committed atomically:

1. **Task 1: User preferences repository and recommendation service with scoring logic** - `dba4ec8` (feat)
2. **Task 2: FastAPI router, lifespan artifact loading, and endpoint tests** - `46b34c8` (feat)

_Note: TDD tasks — RED confirmed by ImportError / 404, GREEN passes all tests_

## Files Created/Modified
- `backend/app/repositories/user_preferences_repo.py` - CRUD for user_preferences collection (get_by_user_id, upsert)
- `backend/app/services/recommendation_service.py` - Scoring logic, mood boost, explanation builder, MOOD_GENRE_MAP
- `backend/app/api/routes/recommendations.py` - POST /api/recommendations + GET /api/recommendations/preferences
- `backend/app/main.py` - Added NLP artifact loading in lifespan + mounted recommendations_router
- `backend/tests/conftest.py` - Added seed_movies fixture (20 docs, tmdb_ids 100-119) and client_with_nlp fixture
- `backend/tests/test_recommendations.py` - Replaced all 9 NotImplementedError stubs with real tests

## Decisions Made
- **seed_movies uses dict copies**: `[dict(m) for m in _SEED_MOVIE_DATA]` prevents mongomock `_id` mutation that caused BulkWriteError on second test run (Rule 1 auto-fix during implementation).
- **client_with_nlp does not insert movies**: Ownership separation — seed_movies inserts, client_with_nlp only sets NLP state. Both share the same `test_db` fixture instance within a test.
- **_get_optional_user**: Decodes JWT without raising on failure, enabling unauthenticated cold-start recommendations. Avoids the OAuth2PasswordBearer 401 requirement for anonymous users.
- **Mood boost after neighbor aggregation**: Candidate genres fetched in one batch query after scoring, not per candidate — efficient for large candidate sets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mongomock BulkWriteError from _id mutation in shared test data**
- **Found during:** Task 1 (running GREEN phase tests)
- **Issue:** `_SEED_MOVIE_DATA` list holds dicts that mongomock mutates by adding `_id` on first `insert_many`. Second fixture invocation reuses those dicts with `_id` already set, triggering E11000 duplicate key errors.
- **Fix:** Changed `seed_movies` fixture to pass `[dict(m) for m in _SEED_MOVIE_DATA]` (shallow copies) instead of the raw list reference. Also refactored `client_with_nlp` to not insert movies — leaving insertion solely to `seed_movies`.
- **Files modified:** backend/tests/conftest.py
- **Verification:** All 9 tests pass, no BulkWriteError
- **Committed in:** dba4ec8 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Required for test correctness. No scope creep; no API or production code changes.

## Issues Encountered
None beyond the mongomock mutation bug documented above.

## User Setup Required
None - no external service configuration required. NLP artifacts from Plan 02-02 must exist in ARTIFACTS_DIR for recommendations to function at runtime (graceful 503 otherwise).

## Self-Check: PASSED

All created files exist and both task commits verified:
- dba4ec8 (Task 1): user_preferences_repo.py, recommendation_service.py, conftest.py, test_recommendations.py
- 46b34c8 (Task 2): recommendations.py router, main.py NLP loading + router mount

## Next Phase Readiness
- POST /api/recommendations fully operational: ready for Plan 02-04 (UI recommendation page integration)
- GET /api/recommendations/preferences available for preference display in UI
- Artifact loading already handles missing files gracefully — worker (Plan 02-02) can run independently
- No blockers for next plan

---
*Phase: 02-content-based-recommendation-engine*
*Completed: 2026-03-26*
