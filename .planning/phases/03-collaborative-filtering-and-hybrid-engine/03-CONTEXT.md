# Phase 3: Collaborative Filtering and Hybrid Engine - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add like/dislike feedback controls to the recommendations page, persist interactions in MongoDB, build an item-based collaborative filtering signal via an offline batch job, blend CF and content-based scores using a configurable hybrid weight, and harden the system with rate limiting and concurrent user support.

NLP pipeline (TF-IDF, similarity index) and content-based recommendation logic are Phase 2 — this phase layers on top of that work without modifying it.

</domain>

<decisions>
## Implementation Decisions

### Feedback UI controls
- Like/dislike buttons appear **below each MovieCard**, next to the explanation text (same row)
- Controls are on the `/recommendations` page only — not on the movie detail page
- Visual state: clicked button highlights/fills with color; user can change vote by clicking the other button (like after dislike replaces the interaction)
- Optimistic update — no page reload needed after feedback
- API: binary only (`like` | `dislike`); clicking the other button replaces the previous interaction (no un-vote/delete logic needed)

### Feedback API
- `POST /api/feedback` — accepts `{ movie_id: int, action: "like" | "dislike" }`
- Authenticated endpoint (JWT required)
- Upserts interaction in MongoDB — same movie can only have one interaction per user

### Collaborative filtering algorithm
- **Item-based CF** — pre-compute a user–movie interaction matrix; find movies liked by users who liked the same movies as the current user
- No neural network (PyTorch NCF is explicitly off the table — unvalidated, over-engineered for sparse capstone data, no GPU guaranteed)
- Runs as an **offline batch job** in the worker (same pattern as `nlp_features.py`) — reads all interactions from MongoDB, computes CF score matrix, writes artifact to disk
- API loads both NLP artifact and CF artifact at startup; CF scores are served from memory at request time (consistent with existing architecture)
- If no CF artifact exists at startup → fall back silently to pure content-based (`alpha = 1.0`); recommendations still work

### CF pre-seeding
- Use **MovieLens-20M** interactions mapped to TMDB IDs
- Mapping strategy: use the `links.csv` file from MovieLens (contains `tmdbId` column) — direct lookup, no fuzzy matching needed
- Ingest a subset of MovieLens ratings (threshold ≥ 4.0 → "like", ≤ 2.0 → "dislike") as synthetic interactions for seeded test users
- A seeding script (e.g., `worker/jobs/seed_interactions.py`) handles the import

### Hybrid blending mechanics
- **Step function at threshold:** if `interaction_count < 5` → `alpha = 1.0` (pure content); if `≥ 5` → `alpha = 0.5` (equal blend)
- Threshold (5) and collaborative weight (0.5) are **env-configurable** (`CF_THRESHOLD`, `CF_ALPHA`)
- **Score formula:** `hybrid_score = alpha * norm(content_score) + (1 - alpha) * norm(cf_score)`
  - Both scores normalized to [0, 1] before blending to prevent scale dominance
  - `norm(x) = (x - min) / (max - min)` across the candidate set for that request

### Rate limiting
- **slowapi** (FastAPI-native, in-memory) — no new infrastructure
- Rate limit applied to `POST /api/recommendations` only (not the feedback endpoint)
- Limit: **10 requests/minute/user** (keyed on JWT user ID)
- Response on limit exceeded: **HTTP 429** with `Retry-After` header (slowapi handles this automatically)
- Frontend should surface a user-facing message: "Too many requests — try again in X seconds"

### Claude's Discretion
- Exact CF artifact format (pickle vs. joblib — use joblib, consistent with NLP artifacts)
- CF score matrix representation (sparse vs. dense — Claude decides based on dataset size)
- Exact slowapi middleware configuration and key function
- Frontend 429 error handling UI (toast vs. inline message)
- Exact `norm()` edge case handling (e.g., when max == min for a candidate set)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 3 — Goal, success criteria, requirement IDs
- `.planning/REQUIREMENTS.md` — DATA-03, REC-03, REC-04, UI-05, API-03, API-07, SEC-03

### Existing backend patterns to follow
- `backend/app/services/recommendation_service.py` — content-based scoring logic; hybrid blending extends this service
- `backend/app/repositories/user_preferences_repo.py` — upsert pattern; new `interactions_repo.py` follows same conventions
- `backend/app/api/routes/recommendations.py` — router pattern; new feedback router follows same structure

### Existing worker patterns to follow
- `worker/jobs/ingest_tmdb.py` — job class pattern; `cf_features.py` follows same structure
- `worker/jobs/` (general) — new `seed_interactions.py` follows same job pattern

### Existing frontend patterns to follow
- `frontend/src/pages/RecommendationsPage.tsx` — current recommendations page; like/dislike buttons added to the per-card div (line ~241)
- `frontend/src/hooks/useRecommendations.ts` — hook pattern; new `useFeedback` mutation hook follows same conventions
- `frontend/src/lib/types.ts` — extend with `FeedbackAction` type and `UserInteraction` type

### External data
- MovieLens-20M `links.csv` — contains `movieId`, `imdbId`, `tmdbId` columns for direct ID mapping

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MovieCard` (frontend/src/components/MovieCard.tsx): Used as-is — like/dislike buttons go in the wrapper div on RecommendationsPage, not inside MovieCard (avoids modifying the shared component)
- `useRecommendations` hook (frontend/src/hooks/useRecommendations.ts): Pattern to follow for new `useFeedback` mutation hook
- `UserPreferencesRepository` (backend/app/repositories/user_preferences_repo.py): Upsert pattern for the new `InteractionsRepository`
- `app_state` in recommendation_service: Already holds TF-IDF artifacts at startup — extend to hold CF artifact too

### Established Patterns
- Offline batch job writes precomputed artifact (joblib) → API loads at startup via lifespan — extend for CF artifact
- JWT `user_id` already extracted in recommendation endpoint via `_get_optional_user` — use `get_current_user` (required, not optional) for feedback endpoint
- Single `.env` at repo root — add `CF_THRESHOLD` and `CF_ALPHA` env vars

### Integration Points
- `backend/app/main.py` lifespan — load CF artifact alongside NLP artifact at startup
- `backend/app/services/recommendation_service.py` — `get_recommendations()` method is where hybrid blending logic is added
- `frontend/src/pages/RecommendationsPage.tsx` — the per-card div (around line 241) is where like/dislike buttons are added
- `worker/` — new `cf_features.py` job + `seed_interactions.py` job added here

</code_context>

<specifics>
## Specific Ideas

- The step function threshold (5 interactions) directly matches the success criteria language — easy to demonstrate in the capstone demo: "before 5 likes, pure content; after 5, collaborative signal kicks in"
- MovieLens `links.csv` has a direct `tmdbId` column — no fuzzy matching or title-based mapping needed, which removes a major implementation risk flagged in STATE.md
- Keep `alpha` and `CF_THRESHOLD` as env variables so the advisor can see them tweaked live during the demo

</specifics>

<deferred>
## Deferred Ideas

- REC-06: Dynamic alpha beyond the step function (smooth ramp, sigmoid) — v2
- Redis-based rate limiting for multi-server deployment — v2
- Like/dislike on the movie detail page — deferred; recommendations page only for v1
- PyTorch NCF — explicitly deferred; not appropriate for this timeline and data volume

</deferred>

---

*Phase: 03-collaborative-filtering-and-hybrid-engine*
*Context gathered: 2026-03-26*
