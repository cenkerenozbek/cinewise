# Phase 2: Content-Based Recommendation Engine - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver personalized, explainable movie recommendations to any user — including a brand-new visitor — using genre/mood preferences + TF-IDF content similarity. Includes:
- NLP batch pipeline in the worker (preprocessing, TF-IDF vectors, precomputed similarity index)
- Recommendation API endpoint (serves precomputed artifacts, no on-request NLP computation)
- Cold-start onboarding UI (genre + mood preference selection)
- Recommendations page displaying Top-K results with explanation text

Like/dislike feedback and collaborative filtering are Phase 3. Rate limiting and concurrent user hardening are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Recommendation display
- Dedicated `/recommendations` route — not embedded in homepage
- Accessed via a "For You" navbar link, visible after login
- If no preferences are set yet, the `/recommendations` page shows the preference form inline (onboarding and results live on the same page — no separate `/onboarding` route)
- Results use the existing `MovieCard` grid layout (reuse `MovieCard` + `MovieGrid` — consistent with browse page)
- Top-K = 10 movies per recommendation session

### Preference onboarding
- Genre selection: multi-select chip/toggle buttons (genres dynamically loaded from DB via existing `/movies/genres` endpoint)
- Mood selection: optional, single-select chips in the same visual style as genre chips; clearly labeled "optional"
- Minimum 1 genre required; mood is optional — validation enforced before fetching recommendations
- Preferences are editable on the `/recommendations` page via an "Edit preferences" button or collapsible section; user can update and re-fetch without leaving the page

### Explanation format
- Short sentence referencing the user's selected preferences: e.g., "Recommended because you like Action and Thriller"
- Explanation rendered in small text below each `MovieCard` (not a tooltip, not behind a click — always visible)

### Mood options (exactly these 5)
- Happy
- Tense
- Relaxing
- Mind-bending
- Romantic

Mood influence on scoring: mood boosts movies whose genres match a predefined mapping (e.g., Tense → Thriller, Horror; Romantic → Romance, Drama; Happy → Comedy, Animation; Relaxing → Documentary, Drama; Mind-bending → Sci-Fi, Mystery). Claude defines the exact genre-to-mood mapping in the implementation.

### Claude's Discretion
- Exact TF-IDF hyperparameters (max_features, ngram_range, stop words)
- Similarity index storage format (pickle, HDF5, or joblib — whatever loads fastest at startup)
- NLP text field composition (overview only, or overview + genre names — researcher to recommend)
- Genre-to-mood boost weight values (e.g., 1.2x multiplier)
- Preferences persistence model (new MongoDB collection vs. field on user document)
- Error/loading states on the recommendations page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 2 — Goal, success criteria, requirement IDs
- `.planning/REQUIREMENTS.md` — NLP-01, NLP-02, NLP-03, NLP-04, REC-01, REC-02, REC-05, UI-02, UI-04, API-02, API-05

### Existing frontend patterns to follow
- `frontend/src/components/MovieCard.tsx` — card component to reuse for recommendation results
- `frontend/src/components/MovieGrid.tsx` — grid component to reuse for displaying results
- `frontend/src/hooks/useMovies.ts` — query hook pattern; create `useRecommendations.ts` following this pattern
- `frontend/src/lib/types.ts` — existing TypeScript types; extend with `RecommendationItem` (adds `explanation: string`)
- `frontend/src/pages/HomePage.tsx` — page structure pattern for new `RecommendationsPage.tsx`
- `frontend/src/components/Navbar.tsx` — add "For You" nav link here

### Existing backend patterns to follow
- `backend/app/api/routes/movies.py` — FastAPI router pattern; create `recommendations.py` following this
- `backend/app/services/movie_service.py` — service layer pattern
- `backend/app/repositories/movie_repo.py` — repository pattern; add `user_preferences_repo.py` following same conventions

### Existing worker patterns to follow
- `worker/jobs/ingest_tmdb.py` — job class pattern; create `nlp_features.py` following same structure
- `worker/pipelines/` (fetch_movies.py, transform.py, load.py) — pipeline stage pattern; NLP pipeline follows same fetch→transform→load structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MovieCard` (frontend/src/components/MovieCard.tsx): Accepts `MovieSummary` prop, renders poster, title, year, rating. Reuse directly for recommendation results — wrap with explanation text below.
- `MovieGrid` (frontend/src/components/MovieGrid.tsx): Renders a grid of `MovieCard`s with loading state. Reuse for recommendations grid.
- `useGenres()` hook (frontend/src/hooks/useMovies.ts): Already fetches genre list from `/movies/genres`. Reuse to populate genre chip options in onboarding form.
- `api.ts` (frontend/src/lib/api.ts): Axios instance with base URL + auth header. Use for `useRecommendations` hook.
- React Query (`@tanstack/react-query`): All data fetching uses `useQuery`. Follow same pattern for recommendations.

### Established Patterns
- Tailwind CSS v4 with `@tailwindcss/vite` — all styling via Tailwind utility classes
- FastAPI router with prefix, mounted in `main.py` — follow for new recommendations router
- Repository layer (movie_repo.py, user_repo.py) — new preferences repo follows same AsyncMongoClient pattern
- Worker job: class in `worker/jobs/`, invoked via pipeline stages in `worker/pipelines/`
- Single `.env` at repo root shared via docker-compose

### Integration Points
- `frontend/src/App.tsx` — register new `/recommendations` route here
- `frontend/src/components/Navbar.tsx` — add "For You" link (visible only when authenticated)
- `backend/app/main.py` — mount new recommendations router
- `worker/jobs/nlp_features.py` (new) — reads from `movies` MongoDB collection, writes TF-IDF artifacts to disk (shared volume)
- `backend/app/main.py` lifespan — load precomputed TF-IDF artifacts at startup (following existing DB connection pattern in lifespan)

</code_context>

<specifics>
## Specific Ideas

- Explanation text must directly reference the user's selected genres: "Recommended because you like [Genre1] and [Genre2]" — not a generic phrase
- The preference form and recommendation results live on the same `/recommendations` page: show form when no preferences exist, show results when preferences are saved
- Mood chips are optional and visually distinct from genre chips (e.g., different label section "How are you feeling?")
- The "Edit preferences" control should be accessible without destroying the current results (e.g., collapsible/expandable section above the grid)

</specifics>

<deferred>
## Deferred Ideas

- Like/dislike feedback on recommendation cards — Phase 3
- Collaborative filtering signal — Phase 3
- Hybrid blending of content + collaborative scores — Phase 3
- Rate limiting on recommendation endpoint — Phase 3
- Watched list / recommendation history — v2
- Bilingual mood labels (TR/EN) — v2 out-of-scope

</deferred>

---

*Phase: 02-content-based-recommendation-engine*
*Context gathered: 2026-03-25*
