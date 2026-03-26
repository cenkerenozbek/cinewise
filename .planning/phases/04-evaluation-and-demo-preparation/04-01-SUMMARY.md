---
phase: 04-evaluation-and-demo-preparation
plan: 01
subsystem: api
tags: [fastapi, pytest, recommendation, metrics, cold-start]

# Dependency graph
requires:
  - phase: 03-collaborative-filtering-and-feedback
    provides: recommendation_service.py with hybrid blending, CF artifact loading in lifespan
provides:
  - GET /api/metrics endpoint returning Precision@10, NDCG@10 from metrics.json
  - Genre fallback to top-rated movies in recommendation_service when no genre match
  - Cold-start robustness tests for genre mismatch, missing CF artifact, obscure movie
affects:
  - 04-02 (evaluation script writes metrics.json consumed by this endpoint)
  - 04-03 (demo preparation relies on metrics endpoint being ready)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Early-return fallback in recommendation service for zero genre-match cold-start"
    - "app.state.metrics loaded from metrics.json at lifespan startup; None when absent"
    - "GET endpoint returns 404 with detail message when state attribute is None"

key-files:
  created:
    - backend/app/api/routes/metrics.py
    - backend/tests/test_metrics.py
  modified:
    - backend/app/services/recommendation_service.py
    - backend/app/main.py
    - backend/tests/test_recommendations.py
    - backend/tests/conftest.py

key-decisions:
  - "Genre fallback returns top-rated movies directly (early return) rather than using them as NLP seeds — avoids empty results when all fallback movies are mutually neighbors and excluded"
  - "metrics.json loaded in lifespan after CF artifact block; app.state.metrics = None when absent so endpoint returns 404 cleanly"
  - "conftest.py client fixture initializes app.state.metrics = None to prevent AttributeError in unrelated tests"

patterns-established:
  - "app.state attributes initialized in both lifespan (production) and conftest fixtures (tests) for all new state fields"
  - "Fallback path returns RecommendationResponse directly, skipping scoring pipeline"

requirements-completed: [EVAL-COLDSTART, EVAL-METRICS-API]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 4 Plan 01: Metrics API and Cold-Start Robustness Summary

**GET /api/metrics endpoint reading metrics.json at startup, plus genre-mismatch fallback returning top-rated movies directly in the recommendation service**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T08:03:14Z
- **Completed:** 2026-03-26T08:05:28Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added genre-mismatch cold-start fallback in recommendation_service.py that returns top-rated movies directly when no DB movies match selected genres
- Created GET /api/metrics endpoint in a new metrics.py router with 200/404 behaviour
- Wired metrics.json loading into the FastAPI lifespan after the CF artifact block
- Added 4 new tests (2 cold-start, 2 metrics) — all 46 backend tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add genre fallback and cold-start tests** - `5e67e2b` (feat)
2. **Task 2: Add GET /api/metrics endpoint with lifespan loading** - `ffc8bc0` (feat)

**Plan metadata:** committed with state update (docs)

## Files Created/Modified
- `backend/app/api/routes/metrics.py` - New router: GET /api/metrics returns loaded metrics or 404
- `backend/tests/test_metrics.py` - Two tests: 200 with data, 404 when None
- `backend/app/services/recommendation_service.py` - Genre fallback early-return block after genre_docs fetch
- `backend/app/main.py` - Added `import json`, metrics_router import, metrics.json lifespan block, router inclusion
- `backend/tests/test_recommendations.py` - Added test_genre_fallback_returns_results, test_obscure_movie_no_cf_neighbors
- `backend/tests/conftest.py` - Added app.state.metrics = None in client fixture

## Decisions Made
- Genre fallback uses an early-return pattern rather than feeding fallback docs into the NLP scoring pipeline. Original approach (substituting genre_docs with top-rated) resulted in empty recommendations because all fallback movies become seeds, their neighbors get scored but are also all seeds, and the exclusion loop empties candidate_scores.
- metrics.json loaded after the CF artifact block in lifespan; state set to None when file absent so the endpoint returns 404 cleanly without requiring a separate flag.
- conftest.py client fixture initialised `app.state.metrics = None` to prevent AttributeError when any test accidentally hits the metrics endpoint path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Genre fallback early-return instead of seed substitution**
- **Found during:** Task 1 (genre fallback implementation)
- **Issue:** Substituting genre_docs with top-rated movies and continuing through the NLP neighbor-scoring pipeline returned empty recommendations. All top-rated fallback movies appear in the NLP index (tmdb_ids 100-119), become seeds, their neighbors are also in the same range, and the seed-exclusion loop removes all candidates.
- **Fix:** Changed to an early-return pattern: fetch top-rated movies directly, build RecommendationResponse, and return before the scoring loop.
- **Files modified:** backend/app/services/recommendation_service.py
- **Verification:** test_genre_fallback_returns_results passes (result.recommendations > 0)
- **Committed in:** 5e67e2b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in implementation approach)
**Impact on plan:** Fix was necessary for correctness. No scope creep. The plan's stated must-have truth ("User selecting genres with zero matching DB movies still receives TOP_K recommendations") is fully satisfied.

## Issues Encountered
- Initial genre fallback substitution produced empty recommendations because the scoring pipeline excludes all seeds from candidates, and when all movies are seeds the candidate set is empty. Fixed by early-return before the scoring loop.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET /api/metrics is live and returns 404 until metrics.json is written by the evaluation script (Plan 04-02)
- Cold-start robustness confirmed for all three scenarios required by Phase 4 SC-1 and SC-3
- Full test suite green (46/46); no regressions introduced

## Self-Check: PASSED

All created files confirmed on disk. Both task commits (5e67e2b, ffc8bc0) confirmed in git log.

---
*Phase: 04-evaluation-and-demo-preparation*
*Completed: 2026-03-26*
