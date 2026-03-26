# Phase 4: Evaluation and Demo Preparation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute and report standard recommendation quality metrics (Precision@10, NDCG@10) against a held-out evaluation set, harden cold-start scenarios to guarantee no empty recommendation lists, and prepare a reliable demo walkthrough with seeded data and a reset script for the capstone presentation and UAT sessions.

Content-based engine, CF hybrid blending, feedback API, and rate limiting are all complete from Phases 2–3. This phase adds evaluation, demo polish, and robustness testing only.

</domain>

<decisions>
## Implementation Decisions

### Evaluation metrics

- **Precision@10 and NDCG@10 only** — K=10 matches the system's Top-10 output; no need to report K=5
- **Evaluation script** — a standalone Python script (`worker/jobs/evaluate.py` or similar) that runs against a held-out subset of MovieLens-20M interactions and prints/stores results
- **Split strategy: leave-one-out per user** — hold out each qualifying test user's most recent liked movie as the ground truth; all their other likes are training signal
- **Minimum 5 likes per test user** — matches CF_THRESHOLD (5 likes = 4 training + 1 test); users below this threshold are excluded from the test set
- **Test set size: 100–500 users** — statistically meaningful for a capstone, fast to compute; randomly sample qualifying users up to 500

### Metrics storage and display

- Eval script writes results to a **`metrics.json` file** in the artifacts directory (same location as NLP/CF `.joblib` files):
  ```json
  { "precision_at_10": X, "ndcg_at_10": Y, "eval_date": "YYYY-MM-DD", "n_users": N }
  ```
- API loads `metrics.json` at startup (alongside joblib artifacts in main.py lifespan); exposes a **`GET /api/metrics`** endpoint that returns the stored values
- Frontend shows a **small metrics card on the Recommendations page, below the page header** — displays Precision@10 and NDCG@10 scores with eval date; card is only shown when metrics are available (API returns data), hidden otherwise
- If `metrics.json` doesn't exist (pre-eval), the `/api/metrics` endpoint returns 404 and the frontend card is hidden — no broken UI

### Demo data and reset

- **Two demo accounts pre-seeded:**
  1. `demo_returning` — user with 5+ interactions (likes), shows CF-blended hybrid recommendations
  2. `demo_coldstart` — fresh user account with no interactions, shows pure content-based cold-start flow
- **Fresh registration live during the demo** — the presenter also registers a brand-new account to show the full onboarding (registration → genre/mood selection → first recommendations)
- **Demo reset script** (`scripts/reset_demo.py` or `worker/jobs/reset_demo.py`) — CLI script that:
  1. Removes any interactions added to `demo_returning` and `demo_coldstart` since last reset
  2. Re-seeds `demo_returning` with its canonical set of 5+ MovieLens-mapped likes
  3. Deletes any test accounts registered during UAT sessions (configurable prefix or by creation date)
  4. Prints a confirmation summary

### UAT sessions

- **Each student gets a fresh account** — UAT participants register a new account at the start of their session; this tests the full cold-start → preference → recommendation flow
- Run `reset_demo.py` between UAT participants to clear stale data
- Success criteria: at least 5 students complete a full session without a crash or unhandled error

### Cold-start robustness

- **New user / no genre match fallback:** If selected genres produce zero seed movies in the DB (extremely rare but possible), `recommendation_service.py` falls back to globally top-rated movies — ensures K results are always returned; no empty lists
- **Sparse system / missing CF artifact:** When CF artifact is missing, empty, or effectively has no valid neighbors, system behaves as pure content-based (`alpha = 1.0`). Already handled via CF artifact stubs (`cf_top_indices=None`) in `main.py` lifespan — explicit test coverage required to confirm no empty results
- **Obscure movie with no CF neighbors:** If a candidate movie has no CF neighbors (zero scores), its CF contribution defaults to `0.0`; the hybrid formula still runs with content score only for that movie — this is effectively `alpha=1.0` per-movie. No code change needed; test coverage required
- All three cold-start scenarios must be covered by explicit test cases in the eval suite

### Claude's Discretion

- Exact metrics card visual design (size, placement, color scheme)
- Eval script argument parsing (CLI flags for artifact path, test set size, output path)
- Whether metrics card shows a tooltip explaining what Precision@10/NDCG@10 mean
- Whether the reset script supports a `--dry-run` flag

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and success criteria
- `.planning/ROADMAP.md` §Phase 4 — Goal, success criteria (Precision@K, NDCG@K, UAT, cold-start, demo walkthrough)
- `.planning/PROJECT.md` — Capstone context, evaluation requirements, MovieLens-20M data source

### Existing backend patterns to follow
- `backend/app/main.py` — lifespan function where artifacts are loaded at startup; `metrics.json` loading follows same pattern as joblib artifacts
- `backend/app/api/routes/recommendations.py` — router pattern for new `/api/metrics` endpoint
- `backend/app/services/recommendation_service.py` — `get_recommendations()` method; genre fallback logic and cold-start alpha handling added here

### Existing worker patterns to follow
- `worker/jobs/cf_features.py` — offline batch job pattern; `evaluate.py` follows same structure
- `worker/jobs/seed_interactions.py` — seeding pattern; `reset_demo.py` follows same conventions

### Existing frontend patterns to follow
- `frontend/src/pages/RecommendationsPage.tsx` — metrics card inserted below page header in this file
- `frontend/src/hooks/useRecommendations.ts` — hook pattern; new `useMetrics` hook follows same conventions

### External data
- MovieLens-20M `links.csv` — `tmdbId` column used for ID mapping (already used in seed_interactions.py)
- MovieLens-20M ratings — `ratings.csv` with `userId`, `movieId`, `rating`, `timestamp`; leave-one-out split uses `timestamp` for ordering

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `worker/jobs/seed_interactions.py`: The seeding pattern + MovieLens `links.csv` mapping is already implemented — evaluate.py and reset_demo.py can import or replicate this logic
- `recommendation_service.py` `_norm()` and `_get_alpha()`: Already handle the CF/content blend edge cases; cold-start tests validate these functions in isolation
- `MovieCard` + `RecommendationsPage.tsx`: Metrics card sits above the movie grid, below the preference form — no changes to `MovieCard` needed

### Established Patterns
- Joblib artifact loading at API startup via `main.py` lifespan — `metrics.json` follows same startup-load pattern
- Single `.env` at repo root — no new env vars needed for Phase 4 (CF_THRESHOLD and CF_ALPHA already set)
- Offline batch worker scripts in `worker/jobs/` — evaluate.py and reset_demo.py go here

### Integration Points
- `backend/app/main.py` lifespan: load `metrics.json` → store on `app.state.metrics` (None if file not found)
- New `GET /api/metrics` route: returns `app.state.metrics` or 404
- `frontend/src/pages/RecommendationsPage.tsx`: conditional metrics card block added at top of results section
- `recommendation_service.py` `get_recommendations()`: add genre-match fallback (top-rated movies) when `genre_docs` is empty

</code_context>

<specifics>
## Specific Ideas

- The leave-one-out split naturally pairs with the "most recent interaction" pattern already used in MovieLens (sorted by timestamp) — no custom split logic needed beyond sorting by timestamp and holding out the last row per user
- `demo_returning` account should have exactly 5+ likes mapped to real TMDB IDs in the DB — enough to trigger CF blend during the live demo (CF_THRESHOLD=5)
- Metrics card in the UI should show something like: `Precision@10: 0.XX | NDCG@10: 0.XX | Evaluated on N users` — a single clean line, not a full dashboard
- The reset script confirmation output should clearly show what was deleted and what was re-seeded, so the presenter knows the system is in a clean state

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-evaluation-and-demo-preparation*
*Context gathered: 2026-03-26*
