# Phase 1: Foundation and Data Pipeline - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Project scaffold, MongoDB setup, TMDB batch ingestion pipeline, user authentication (register/login), and movie search/browse UI. NLP processing, recommendations, and feedback controls are Phase 2+.

</domain>

<decisions>
## Implementation Decisions

### Project structure
- Monorepo with `backend/`, `frontend/`, `worker/` at root
- `shared/` directory at root for MongoDB models and config shared between backend and worker
- `artifacts/` directory at root for precomputed TF-IDF/similarity files (Phase 2+)
- `scripts/`, `.env.example`, `docker-compose.yml`, `README.md` at repo root
- Backend layout: `app/api/routes`, `app/services`, `app/repositories`, `app/models`, `app/core`, `tests/`
- Frontend layout: `src/pages`, `src/components`, `src/features`, `src/lib`, `src/hooks`
- Worker layout: `jobs/`, `pipelines/`, `tests/`
- Full docker-compose.yml with backend, frontend, worker, and local MongoDB services
- Single `.env` at repo root shared by all services (MONGO_URI, TMDB_API_KEY, JWT_SECRET, etc.)

### TMDB ingestion scope
- Target ~5,000 movies (popular + top-rated)
- Fetch via TMDB `/movie/popular` and `/movie/top_rated` endpoints, paginate and deduplicate until target count reached
- Per-movie data: title, year, genres, overview, poster URL, rating, vote_count, popularity, plus top 5 cast and director from `/credits` endpoint, Turkish title from translations
- Full re-ingest (upsert) each run — no incremental tracking
- Retry with exponential backoff on TMDB API failures; already-ingested data preserved

### Auth pattern
- JWT access token only — no refresh tokens for v1
- Token expiry: 12-24 hours (sufficient for capstone demo sessions)
- Endpoints: `POST /register`, `POST /login`
- bcrypt password hashing
- Bearer token on protected API endpoints
- Registration collects email + password only (display name optional/derived)
- Auth is intentionally minimal — recommendation engine is the core focus

### Movie search UI
- Debounced real-time search (300ms) with genre and year filter dropdowns
- Results displayed as poster grid: poster image, title, year, rating badge
- Click on card navigates to dedicated detail page (`/movie/:id`) with full info: poster, title, year, genres, director, top cast, summary, rating
- Landing page shows popular movies grid as default view; search/filters refine this set

### Claude's Discretion
- Exact Docker service configuration and networking
- MongoDB collection schema design and indexing strategy
- API response pagination approach for search results
- Frontend styling framework/approach (Tailwind, CSS modules, etc.)
- Error handling UI patterns (toasts, error pages)
- Loading states and skeleton designs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Tech stack, constraints, team structure, key decisions
- `.planning/REQUIREMENTS.md` — Full v1 requirement list with phase mapping (DATA-01, DATA-02, DATA-04, DATA-05, DATA-06, UI-01, UI-03, API-01, API-04, API-06, SEC-01, SEC-02 for this phase)
- `.planning/ROADMAP.md` — Phase 1 success criteria and dependency chain

### Capstone proposal
- `2025_Capstone_Project_Proposal_Template.pdf` — Original capstone proposal with project scope and evaluation criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — greenfield project

### Established Patterns
- No patterns yet — Phase 1 establishes the foundation patterns

### Integration Points
- MongoDB Atlas free tier as primary datastore
- TMDB API as external data source (rate-limited)
- Worker connects to same MongoDB as backend via shared models
- Frontend connects to backend REST API

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose dedicated detail page over modal overlay for movie details — prefers full-page navigation
- Auth kept deliberately simple (JWT access only, no refresh) to focus capstone effort on recommendation engine
- Worker is a separate process/service, not embedded in the backend — clean separation of batch and serving concerns

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-and-data-pipeline*
*Context gathered: 2026-03-25*
