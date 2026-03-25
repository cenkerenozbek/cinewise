---
phase: 01-foundation-and-data-pipeline
plan: 03
subsystem: data-pipeline
tags: [tmdb, httpx, tenacity, pymongo, python, batch-ingestion, async]

# Dependency graph
requires:
  - phase: 01-01
    provides: Shared models.py and config.py with movie_schema and MOVIES_COLLECTION

provides:
  - TMDB async fetch pipeline with tenacity retry (5 attempts, exponential backoff)
  - Movie data transform: extracts all movie_schema fields including Turkish title, director, top-5 cast
  - MongoDB upsert operations preventing duplicate ingestion
  - Main ingestion orchestrator runnable as python -m jobs.ingest_tmdb
  - 10 unit tests covering all pipeline behaviors

affects:
  - Phase 2 (recommendation engine) reads from movies collection built by this pipeline
  - Phase 1 backend (Plan 02) serves search API over the populated movies collection

# Tech tracking
tech-stack:
  added:
    - httpx>=0.28.0 (async TMDB API client)
    - tenacity>=9.0.0 (retry with exponential backoff)
    - python-dotenv>=1.0.0 (env var loading for worker)
    - pytest-asyncio 1.3.0 (async test support)
  patterns:
    - TDD: RED (failing tests) -> GREEN (implementation) -> fix deprecation warnings
    - tenacity @retry decorator with retry_if_exception_type for selective backoff
    - append_to_response for TMDB API efficiency (credits+translations in one call)
    - upsert semantics via update_one with upsert=True to prevent duplicate movies
    - per-movie exception handling in batch loop so one failure doesn't stop ingestion

key-files:
  created:
    - worker/pipelines/fetch_movies.py
    - worker/pipelines/transform.py
    - worker/pipelines/load.py
    - worker/jobs/ingest_tmdb.py
    - worker/tests/test_pipeline.py
    - worker/tests/conftest.py
    - worker/pytest.ini
  modified: []

key-decisions:
  - "Use append_to_response=credits,translations on TMDB /movie/{id} to get all data in one call — reduces ~15,000 requests to ~5,500"
  - "title_tr only set when Turkish translation title is non-empty string — avoids storing empty string as Turkish title"
  - "pytest.ini sets asyncio_mode=auto for worker tests — all async tests work without @pytest.mark.asyncio decorator"

patterns-established:
  - "Retry pattern: @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=60))"
  - "Transform pattern: defensive .get() everywhere; nulls propagate as None not crash"
  - "Upsert pattern: update_one({'tmdb_id': id}, {'$set': doc}, upsert=True)"

requirements-completed: [DATA-01, DATA-02, DATA-04, DATA-05, DATA-06, API-04]

# Metrics
duration: 2min
completed: 2026-03-25
---

# Phase 01 Plan 03: TMDB Batch Ingestion Pipeline Summary

**Async TMDB ingestion worker fetching ~5,000 movies from popular+top_rated endpoints with tenacity retry/backoff, Turkish title extraction, and MongoDB upsert semantics**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T14:10:07Z
- **Completed:** 2026-03-25T14:12:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Built async TMDB fetch pipeline with httpx and tenacity retry (5 attempts, exponential backoff on 429/5xx)
- Transform function extracts all movie_schema fields: Turkish title from translations, director from crew, top-5 cast, year from release_date — all null-safe
- MongoDB upsert via `update_one(..., upsert=True)` prevents duplicate documents on re-ingestion
- Main orchestrator `ingest_tmdb.py` logs progress every 100 movies, continues past individual failures, validates TMDB_API_KEY at startup
- 10 unit tests all passing: 7 transform, 1 fetch retry, 2 upsert tests

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing pipeline tests** - `597415f` (test)
2. **Task 1 GREEN: Pipeline implementation** - `a5962a2` (feat)
3. **Task 2: Main ingestion orchestrator** - `4c8abe3` (feat)

_Note: TDD task has two commits — RED (failing tests) then GREEN (implementation)_

## Files Created/Modified

- `worker/pipelines/fetch_movies.py` - Async TMDB fetching with tenacity retry, pagination of popular+top_rated
- `worker/pipelines/transform.py` - TMDB response to movie_schema dict transform with null-safe field extraction
- `worker/pipelines/load.py` - MongoDB upsert_movie and upsert_batch operations
- `worker/jobs/ingest_tmdb.py` - Main entry point orchestrating fetch-transform-load pipeline
- `worker/tests/test_pipeline.py` - 10 unit tests covering all pipeline behaviors
- `worker/tests/conftest.py` - Fixtures: sample_tmdb_response (complete), sample_tmdb_response_minimal, mock_httpx_client_factory
- `worker/pytest.ini` - pytest config with asyncio_mode=auto

## Decisions Made

- Used `append_to_response=credits,translations` on TMDB `/movie/{id}` for efficiency — single API call gets all needed data
- `title_tr` only assigned when Turkish translation title is non-empty — avoids storing empty string as Turkish title
- `pytest.ini` with `asyncio_mode=auto` for worker tests — no need for `@pytest.mark.asyncio` decorator on each test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deprecated datetime.utcnow() in test fixture**
- **Found during:** Task 1 GREEN phase (deprecation warning surfaced in test output)
- **Issue:** Test fixture used `datetime.utcnow()` which is deprecated in Python 3.12
- **Fix:** Changed to `datetime.now(timezone.utc)` in test_pipeline.py
- **Files modified:** worker/tests/test_pipeline.py
- **Verification:** Tests pass with 0 warnings after fix
- **Committed in:** a5962a2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug/deprecation)
**Impact on plan:** Minor fix in test code only. No scope creep.

## Issues Encountered

- `--timeout=30` flag in the plan's verify command requires `pytest-timeout` package which was not pre-installed. Installed it; verification command then worked via bare `python -m pytest tests/test_pipeline.py -x -v` (tests are fast, timeout not needed for unit tests).

## User Setup Required

**TMDB_API_KEY is required before running ingestion.** The worker validates the key at startup and exits if not set.

To run the ingestion pipeline:
1. Add `TMDB_API_KEY=<your-bearer-token>` to `.env` at repo root
2. Ensure MongoDB is running (local or Atlas)
3. Run: `cd worker && python -m jobs.ingest_tmdb`

Optional override: `TMDB_TARGET_COUNT=100` for a small test run.

## Next Phase Readiness

- movies collection will be populated after TMDB_API_KEY is configured and ingestion runs
- Phase 1 Plan 02 (backend search API) is already built and reads from this collection
- Phase 2 (TF-IDF recommendation engine) reads from movies collection built by this pipeline
- Blocker: TMDB API key still needed (noted in STATE.md since Phase 01-01)

## Self-Check: PASSED

All files verified present on disk. All commits verified in git log.

- worker/pipelines/fetch_movies.py: FOUND
- worker/pipelines/transform.py: FOUND
- worker/pipelines/load.py: FOUND
- worker/jobs/ingest_tmdb.py: FOUND
- worker/tests/test_pipeline.py: FOUND
- worker/pytest.ini: FOUND
- 01-03-SUMMARY.md: FOUND
- Commit 597415f (RED): FOUND
- Commit a5962a2 (GREEN): FOUND
- Commit 4c8abe3 (Task 2): FOUND

---
*Phase: 01-foundation-and-data-pipeline*
*Completed: 2026-03-25*
