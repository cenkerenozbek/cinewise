---
phase: 02-content-based-recommendation-engine
plan: "02"
subsystem: nlp
tags: [tfidf, scikit-learn, joblib, cosine-similarity, nlp, batch-pipeline, mongodb]

# Dependency graph
requires:
  - phase: 02-01
    provides: worker infrastructure, pytest setup, shared/config.py, Pydantic contracts

provides:
  - worker/jobs/nlp_features.py — full NLP batch pipeline (preprocess, TF-IDF, similarity index, artifact persistence)
  - worker/tests/test_nlp_pipeline.py — 8 passing tests covering NLP-01, NLP-02, NLP-03
  - worker/tests/conftest.py — sample_movie_docs fixture (10 movies)

affects:
  - 02-03 (recommendation API loads tfidf_vectorizer.joblib and similarity_index.joblib at startup)
  - 02-04 (integration tests may invoke pipeline against real MongoDB)

# Tech tracking
tech-stack:
  added: []  # scikit-learn, numpy, scipy, joblib already in requirements.txt from 02-01
  patterns:
    - Row-by-row cosine similarity loop for memory-safe large corpus processing
    - min_df fallback (2 -> 1) for small corpus empty-vocabulary guard
    - self-exclusion via sims[i] = -1.0 before argpartition

key-files:
  created:
    - worker/jobs/nlp_features.py
  modified:
    - worker/tests/test_nlp_pipeline.py
    - worker/tests/conftest.py

key-decisions:
  - "Row-by-row cosine_similarity loop (not full matrix multiply) — avoids O(N^2) memory for 5k-movie corpus"
  - "min_df fallback from 2 to 1 for small test corpora — prevents ValueError: empty vocabulary in unit tests"
  - "sims[i] = -1.0 self-exclusion before argpartition — guarantees self never in top-N without conditional checks"
  - "effective_top_n = min(50, N-1) — small corpus safety so argpartition never requests more neighbors than available"

patterns-established:
  - "Pattern: TDD RED commit (failing tests) -> GREEN commit (implementation) — two atomic commits per TDD cycle"
  - "Pattern: preprocess_text handles None via or '' — no caller needs None guard"
  - "Pattern: html.unescape before re.sub for HTML tag stripping — correct entity decoding order"

requirements-completed: [NLP-01, NLP-02, NLP-03]

# Metrics
duration: 2min
completed: 2026-03-26
---

# Phase 02 Plan 02: NLP Batch Pipeline Summary

**TF-IDF NLP batch pipeline with row-by-row cosine similarity index and joblib artifact persistence for 5k-movie corpus**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T04:16:00Z
- **Completed:** 2026-03-26T04:18:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented `preprocess_text` handling HTML entities, tag stripping, None overview coercion, and genre concatenation
- Built TF-IDF vectorizer (max_features=5000, bigrams, English stop words, sublinear TF) with small-corpus min_df fallback
- Built memory-safe row-by-row cosine similarity index (top-50 neighbors per movie, dtype int32, self-excluded)
- Implemented `save_artifacts` persisting vectorizer and similarity index as joblib files to ARTIFACTS_DIR
- Implemented `async def main()` following ingest_tmdb.py MongoDB pattern, pipeline executable standalone
- All 8 NLP pipeline tests pass (NLP-01, NLP-02, NLP-03)

## Task Commits

Each task was committed atomically via TDD:

1. **Task 1: RED phase** - `31fdcfe` (test: failing tests for NLP pipeline)
2. **Task 1+2: GREEN phase** - `ce62100` (feat: full nlp_features.py implementation)

_Note: Implementation covered both tasks in a single GREEN commit since the full pipeline was designed holistically. All 8 tests pass._

## Files Created/Modified

- `worker/jobs/nlp_features.py` — Full NLP batch pipeline: preprocess_text, build_tfidf_matrix, build_similarity_index, save_artifacts, async main (179 lines)
- `worker/tests/test_nlp_pipeline.py` — 8 passing tests for NLP-01/02/03, replacing NotImplementedError stubs (115 lines)
- `worker/tests/conftest.py` — Added sample_movie_docs fixture (10 sample movie docs matching MongoDB shape)

## Decisions Made

- **Row-by-row loop**: Used `cosine_similarity(tfidf_matrix[i], tfidf_matrix)` in a loop instead of full matrix multiply to avoid O(N^2) dense memory allocation for 5k-movie corpus
- **min_df fallback**: Added try/except to fall back from min_df=2 to min_df=1 when corpus is too small for bigram threshold (keeps unit tests working with 10 docs)
- **Self-exclusion via -1.0**: Setting `sims[i] = -1.0` before argpartition is simpler and faster than post-filtering
- **effective_top_n cap**: `min(50, N-1)` prevents argpartition from requesting more neighbors than available rows

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria met on first implementation attempt.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `worker/jobs/nlp_features.py` is ready to run after MongoDB is populated (Phase 01 ingestion)
- Artifacts `/artifacts/tfidf_vectorizer.joblib` and `/artifacts/similarity_index.joblib` produced by pipeline
- Phase 02-03 recommendation API can load these artifacts at startup for sub-millisecond per-request recommendations

---
*Phase: 02-content-based-recommendation-engine*
*Completed: 2026-03-26*

## Self-Check: PASSED

- worker/jobs/nlp_features.py: FOUND
- worker/tests/test_nlp_pipeline.py: FOUND
- .planning/phases/02-content-based-recommendation-engine/02-02-SUMMARY.md: FOUND
- Commit ce62100: FOUND
- Commit 31fdcfe: FOUND
