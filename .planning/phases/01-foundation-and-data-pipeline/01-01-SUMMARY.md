---
phase: 01-foundation-and-data-pipeline
plan: 01
subsystem: infra
tags: [fastapi, pymongo, docker, vite, react, tailwindcss, pydantic-settings, mongodb, typescript]

# Dependency graph
requires: []
provides:
  - "docker-compose.yml with 4 services: mongo, backend, frontend, worker"
  - "FastAPI skeleton with AsyncMongoClient lifespan, CORS, /api/health endpoint"
  - "Pydantic BaseSettings loading MONGO_URI, TMDB_API_KEY, JWT_SECRET from .env"
  - "shared/models.py movie_schema and user_schema document contracts"
  - "shared/config.py MOVIES_COLLECTION and USERS_COLLECTION constants"
  - "React/Vite frontend with BrowserRouter, TanStack Query, axios JWT interceptor"
  - "Tailwind CSS v4 @tailwindcss/vite plugin"
  - "backend/tests/conftest.py AsyncClient + ASGITransport fixture"
  - "backend/pyproject.toml pytest asyncio_mode=auto"
  - "worker/tests/conftest.py placeholder"
affects: [01-02, 01-03, 01-04, all subsequent plans]

# Tech tracking
tech-stack:
  added:
    - "fastapi[standard]>=0.115.0"
    - "pymongo>=4.10.0 (AsyncMongoClient — NOT Motor)"
    - "pydantic-settings>=2.13.0"
    - "python-jose[cryptography]>=3.3.0"
    - "passlib[bcrypt]>=1.7.0"
    - "httpx>=0.28.0"
    - "tenacity>=9.0.0"
    - "mongomock>=4.2.0"
    - "pytest>=8.0.0 + pytest-asyncio>=0.24.0"
    - "react 19 + react-router-dom 7 + @tanstack/react-query 5"
    - "axios 1.x"
    - "tailwindcss 4 + @tailwindcss/vite"
  patterns:
    - "FastAPI lifespan context manager for MongoDB connection lifecycle"
    - "AsyncMongoClient (NOT Motor — deprecated May 2025)"
    - "Pydantic BaseSettings with env_file for configuration"
    - "Repository pattern for MongoDB operations"
    - "Axios interceptor for JWT Bearer token injection"
    - "TanStack Query for server state management"

key-files:
  created:
    - "docker-compose.yml"
    - ".env.example"
    - ".gitignore"
    - "backend/app/main.py"
    - "backend/app/core/config.py"
    - "backend/app/core/database.py"
    - "backend/requirements.txt"
    - "backend/Dockerfile"
    - "backend/pyproject.toml"
    - "backend/tests/conftest.py"
    - "shared/models.py"
    - "shared/config.py"
    - "worker/Dockerfile"
    - "worker/requirements.txt"
    - "frontend/vite.config.ts"
    - "frontend/src/main.tsx"
    - "frontend/src/App.tsx"
    - "frontend/src/lib/api.ts"
    - "frontend/src/index.css"
    - "frontend/Dockerfile"
    - "scripts/seed.sh"
  modified:
    - ".gitignore"

key-decisions:
  - "Use PyMongo AsyncMongoClient directly — Motor deprecated May 2025, EOL May 2026"
  - "FastAPI lifespan context manager for DB connection + index creation at startup"
  - "Single .env at repo root shared by all services via docker-compose env_file"
  - "Tailwind CSS v4 with @tailwindcss/vite plugin (not v3 PostCSS approach)"
  - "JWT_SECRET default in config.py is a placeholder — must be overridden in .env"

patterns-established:
  - "Pattern 1 (lifespan): AsyncMongoClient created in FastAPI lifespan, stored in app.state.db"
  - "Pattern 2 (config): Pydantic BaseSettings with model_config dict (not class Config — Pydantic v2)"
  - "Pattern 3 (db-dep): get_db FastAPI dependency reads request.app.state.db"
  - "Pattern 4 (tests): ASGITransport + AsyncClient for async endpoint testing"
  - "Pattern 5 (api-client): axios.create + interceptors.request for JWT injection"

requirements-completed: [SEC-01, DATA-05]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 1 Plan 01: Monorepo Scaffold and Frontend Foundation Summary

**4-service Docker Compose monorepo with FastAPI/AsyncMongoClient backend skeleton, Tailwind v4 React/Vite frontend, shared MongoDB schemas, and pytest/httpx test scaffolds**

## Performance

- **Duration:** 3 minutes
- **Started:** 2026-03-25T13:55:19Z
- **Completed:** 2026-03-25T13:59:17Z
- **Tasks:** 2 of 2
- **Files modified:** 40+ files created across backend/, frontend/, worker/, shared/, scripts/

## Accomplishments

- Buildable monorepo with all 4 Docker services (mongo, backend, frontend, worker) defined in docker-compose.yml
- FastAPI skeleton with AsyncMongoClient lifespan, MongoDB text/compound indexes at startup, CORSMiddleware, /api/health endpoint
- React/Vite frontend with BrowserRouter, TanStack Query, axios JWT interceptor, Tailwind CSS v4 — npm run build passes clean (71 modules)
- Shared MongoDB document schemas (movie_schema, user_schema) and collection constants establishing the contract between backend and worker
- Complete test scaffolding: pytest asyncio_mode=auto, ASGITransport+AsyncClient fixture in backend/tests/conftest.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Monorepo scaffold with Docker Compose and shared configuration** - `e467c01` (chore)
2. **Task 2: React/Vite frontend scaffold with Tailwind, routing, and test config** - `71b2dce` (feat)
3. **Frontend README and dist cleanup** - `91be6b6` (chore)

**Plan metadata:** (docs commit — created after this summary)

## Files Created/Modified

- `docker-compose.yml` — 4 services: mongo:7, backend:8000, frontend:5173, worker; named volume mongo_data
- `.env.example` — MONGO_URI, DB_NAME, TMDB_API_KEY, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, VITE_API_URL
- `.gitignore` — Python, Node, .env (not .env.example), artifacts/
- `backend/app/main.py` — FastAPI app with lifespan, AsyncMongoClient, index creation, CORS, /api/health
- `backend/app/core/config.py` — Pydantic BaseSettings class Settings with all env vars
- `backend/app/core/database.py` — get_db FastAPI dependency returning AsyncDatabase from app.state
- `backend/requirements.txt` — fastapi, pymongo, pydantic-settings, python-jose, passlib, httpx, tenacity, mongomock, pytest
- `backend/Dockerfile` — python:3.12-slim, uvicorn --reload
- `backend/pyproject.toml` — pytest asyncio_mode=auto
- `backend/tests/conftest.py` — AsyncClient + ASGITransport test fixture
- `shared/models.py` — movie_schema and user_schema dict contracts
- `shared/config.py` — MOVIES_COLLECTION, USERS_COLLECTION constants
- `worker/Dockerfile` — python:3.12-slim, CMD python -m jobs.ingest_tmdb
- `worker/requirements.txt` — pymongo, httpx, tenacity, python-dotenv, pytest
- `worker/tests/conftest.py` — placeholder for TMDB mock fixtures
- `frontend/vite.config.ts` — react + tailwindcss plugins, server host 0.0.0.0:5173
- `frontend/src/main.tsx` — StrictMode > QueryClientProvider > BrowserRouter > App
- `frontend/src/App.tsx` — Routes shell with placeholder home route
- `frontend/src/lib/api.ts` — axios instance with JWT Bearer token interceptor
- `frontend/src/index.css` — @import "tailwindcss" (v4 approach)
- `frontend/Dockerfile` — node:22-alpine, npm install, npm run dev --host
- `scripts/seed.sh` — docker-compose up mongo + docker-compose run worker

## Decisions Made

- Used PyMongo `AsyncMongoClient` directly (not Motor — Motor deprecated May 2025, EOL May 2026). This is the critical tech decision for all subsequent backend plans.
- Tailwind CSS v4 with `@tailwindcss/vite` plugin — different from v3 PostCSS approach; `@import "tailwindcss"` replaces `@tailwind` directives.
- `JWT_SECRET` has a placeholder default in config.py with `extra="ignore"` to prevent validation errors when running without a full .env. Production must override this.
- MongoDB indexes (text index on movies.title, compound on genres+year) created at FastAPI startup via lifespan — ensures indexes exist before any queries run.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required in this plan. TMDB API key is needed for Plan 02 (data ingestion) — already documented in STATE.md blockers.

## Next Phase Readiness

- Plans 01-02, 01-03, 01-04 can all build on this foundation
- Docker Compose services are defined and buildable
- Backend module structure (app/api/routes, app/services, app/repositories, app/models) is empty but directories and __init__.py stubs are in place
- Frontend page/component directories (src/pages, src/components, src/features, src/hooks) still need to be created — Plan 01-04 handles the UI
- TMDB API key still needed before data ingestion worker can run (Plan 01-02 blocker)

---
*Phase: 01-foundation-and-data-pipeline*
*Completed: 2026-03-25*
