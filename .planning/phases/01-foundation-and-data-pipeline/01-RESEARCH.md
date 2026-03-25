# Phase 1: Foundation and Data Pipeline - Research

**Researched:** 2026-03-25
**Domain:** Project scaffold, FastAPI + MongoDB backend, TMDB batch ingestion, JWT auth, React search UI
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield setup covering four major workstreams: (1) monorepo scaffold with Docker Compose, (2) TMDB batch ingestion worker, (3) FastAPI backend with JWT auth and movie search API, and (4) React/TypeScript frontend with movie browsing and search. The tech stack is well-established (FastAPI, PyMongo async, React/Vite) with strong community patterns.

The most critical technical decision is using PyMongo's native async API (`AsyncMongoClient`) instead of Motor, since Motor was deprecated on May 14, 2025 and reaches end-of-life on May 14, 2026. For TMDB ingestion, the API has generous rate limits (~40-50 req/s) but the worker must handle 429 errors gracefully and use upsert semantics to preserve already-ingested data.

**Primary recommendation:** Use PyMongo 4.x with `AsyncMongoClient` for all async MongoDB operations. Use `httpx` for both TMDB API calls (async) and FastAPI test client. Keep auth minimal (JWT access-only, bcrypt via passlib) to stay focused on the recommendation engine in later phases.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Monorepo with `backend/`, `frontend/`, `worker/` at root
- `shared/` directory at root for MongoDB models and config shared between backend and worker
- `artifacts/` directory at root for precomputed TF-IDF/similarity files (Phase 2+)
- `scripts/`, `.env.example`, `docker-compose.yml`, `README.md` at repo root
- Backend layout: `app/api/routes`, `app/services`, `app/repositories`, `app/models`, `app/core`, `tests/`
- Frontend layout: `src/pages`, `src/components`, `src/features`, `src/lib`, `src/hooks`
- Worker layout: `jobs/`, `pipelines/`, `tests/`
- Full docker-compose.yml with backend, frontend, worker, and local MongoDB services
- Single `.env` at repo root shared by all services
- Target ~5,000 movies (popular + top-rated) via TMDB `/movie/popular` and `/movie/top_rated`
- Per-movie: title, year, genres, overview, poster URL, rating, vote_count, popularity, top 5 cast, director, Turkish title from translations
- Full re-ingest (upsert) each run -- no incremental tracking
- Retry with exponential backoff on TMDB failures; already-ingested data preserved
- JWT access token only -- no refresh tokens
- Token expiry: 12-24 hours
- Endpoints: `POST /register`, `POST /login`
- bcrypt password hashing
- Bearer token on protected API endpoints
- Registration: email + password only (display name optional/derived)
- Debounced real-time search (300ms) with genre and year filter dropdowns
- Results as poster grid: poster image, title, year, rating badge
- Click navigates to dedicated detail page (`/movie/:id`)
- Landing page shows popular movies grid as default view

### Claude's Discretion
- Exact Docker service configuration and networking
- MongoDB collection schema design and indexing strategy
- API response pagination approach for search results
- Frontend styling framework/approach (Tailwind, CSS modules, etc.)
- Error handling UI patterns (toasts, error pages)
- Loading states and skeleton designs

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Collect movie metadata from TMDB API (title, year, genres, cast, director, summary, poster URL, rating, vote count) | TMDB API endpoints documented; `httpx` async client for batch fetching; upsert pattern for MongoDB |
| DATA-02 | Store original and Turkish titles when available | TMDB `/movie/{id}/translations` endpoint provides `tr` locale data; store as `title_tr` field |
| DATA-04 | Handle missing metadata fields without breaking | Pydantic models with `Optional` fields and defaults; defensive parsing in worker pipeline |
| DATA-05 | Run offline batch pipeline for data ingestion | Standalone `worker/` service with Python script; Docker service in compose |
| DATA-06 | Batch pipeline completes within 2 hours for target dataset | ~5,000 movies with ~3 API calls each (list page + details+credits + translations) = ~15,000 requests; at 30 req/s conservative pace = ~8 minutes; well within 2h |
| UI-01 | User can register and login | React login/register forms; JWT token stored in localStorage; auth context provider |
| UI-03 | User can search movies by title and filter by genre/year | Debounced search input + filter dropdowns; TanStack Query for data fetching; poster grid display |
| API-01 | REST endpoints for movie listing/search/filtering | FastAPI routes with query params (q, genre, year, page); MongoDB text index + compound filters |
| API-04 | TMDB API integration with retry/backoff error handling | `httpx` with `tenacity` retry library; exponential backoff on 429/5xx |
| API-06 | Search API responds within 2 seconds (p95) | MongoDB text index on title; compound index on genre+year; limit result set with pagination |
| SEC-01 | Persist users, movies, interactions in MongoDB | PyMongo async with `AsyncMongoClient`; `users` and `movies` collections in Phase 1 |
| SEC-02 | Store passwords using bcrypt hashing | `passlib[bcrypt]` CryptContext; hash on registration, verify on login |
</phase_requirements>

## Standard Stack

### Backend (Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | ~0.115+ | Web framework | Official choice per PROJECT.md; async-native, Pydantic integration |
| uvicorn | ~0.34+ | ASGI server | FastAPI's standard server |
| pymongo | ~4.10+ | MongoDB driver (async) | Native `AsyncMongoClient` replaces deprecated Motor |
| pydantic | ~2.10+ | Data validation/serialization | FastAPI's built-in validation layer |
| pydantic-settings | ~2.13+ | Environment config | `.env` file loading with type validation |
| python-jose[cryptography] | ~3.3+ | JWT token creation/verification | FastAPI docs standard for JWT |
| passlib[bcrypt] | ~1.7+ | Password hashing | FastAPI docs standard for bcrypt |
| python-multipart | ~0.0.18+ | Form data parsing | Required for OAuth2PasswordRequestForm |
| httpx | ~0.28+ | Async HTTP client | For TMDB API calls and test client |
| tenacity | ~9.0+ | Retry with backoff | Exponential backoff for TMDB API failures |

### Worker (Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymongo | ~4.10+ | MongoDB driver (sync or async) | Shared models with backend; sync is fine for batch worker |
| httpx | ~0.28+ | HTTP client for TMDB | Async batch requests with connection pooling |
| tenacity | ~9.0+ | Retry logic | Exponential backoff on TMDB 429/5xx |
| python-dotenv | ~1.0+ | Env loading | Load root `.env` in worker scripts |

### Frontend (TypeScript/React)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ~19.x | UI framework | Project tech stack |
| react-dom | ~19.x | DOM rendering | Paired with React |
| vite | ~6.x | Build tool | Modern React standard, fast HMR |
| typescript | ~5.7+ | Type safety | Project requirement |
| react-router-dom | ~7.x | Client-side routing | Standard React router |
| @tanstack/react-query | ~5.x | Server state management | Data fetching, caching, loading states |
| axios | ~1.7+ | HTTP client | API calls with interceptors for JWT |
| tailwindcss | ~4.x | Utility CSS | Rapid UI development (Claude's discretion) |
| shadcn/ui | latest | Component library | Accessible, Tailwind-native components (Claude's discretion) |

### Dev/Testing
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ~8.x | Python test runner | Standard for FastAPI projects |
| pytest-asyncio | ~0.24+ | Async test support | For testing async FastAPI endpoints |
| httpx | ~0.28+ | Async test client | FastAPI async testing (replaces TestClient for async) |
| mongomock | ~4.2+ | MongoDB mock | In-memory MongoDB for unit tests |
| vitest | ~3.x | Frontend test runner | Vite-native, fast, TypeScript support |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMongo async | Motor | Motor deprecated May 2025, EOL May 2026 -- avoid |
| httpx | aiohttp | httpx has sync+async in one API, better for FastAPI test client too |
| Tailwind CSS | CSS Modules | Tailwind is faster for prototyping; capstone has tight timeline |
| axios | fetch/ky | axios interceptors simplify JWT token injection |
| tenacity | manual retry | tenacity handles jitter, max retries, exception filtering out of box |

**Installation (Backend):**
```bash
pip install "fastapi[standard]" pymongo pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" python-multipart httpx tenacity
```

**Installation (Worker):**
```bash
pip install pymongo httpx tenacity python-dotenv
```

**Installation (Frontend):**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query axios
npx shadcn@latest init
npx tailwindcss@latest init
```

## Architecture Patterns

### Recommended Project Structure
```
ai-powered-mrs/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, lifespan, CORS
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings BaseSettings
│   │   │   ├── database.py      # AsyncMongoClient setup
│   │   │   └── security.py      # JWT + bcrypt helpers
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py      # POST /register, POST /login
│   │   │       └── movies.py    # GET /movies, GET /movies/{id}, GET /movies/search
│   │   ├── models/
│   │   │   ├── user.py          # Pydantic user models
│   │   │   └── movie.py         # Pydantic movie models
│   │   ├── repositories/
│   │   │   ├── user_repo.py     # MongoDB user CRUD
│   │   │   └── movie_repo.py    # MongoDB movie queries
│   │   └── services/
│   │       ├── auth_service.py  # Registration/login logic
│   │       └── movie_service.py # Search/filter business logic
│   ├── tests/
│   │   ├── conftest.py          # Fixtures, test DB setup
│   │   ├── test_auth.py
│   │   └── test_movies.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx     # Popular movies grid
│   │   │   ├── MovieDetailPage.tsx  # /movie/:id
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── components/
│   │   │   ├── MovieCard.tsx
│   │   │   ├── MovieGrid.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FilterDropdowns.tsx
│   │   │   └── Navbar.tsx
│   │   ├── features/
│   │   │   └── auth/
│   │   │       └── AuthContext.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # axios instance with JWT interceptor
│   │   │   └── utils.ts
│   │   ├── hooks/
│   │   │   ├── useMovies.ts     # TanStack Query hooks
│   │   │   └── useAuth.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── worker/
│   ├── jobs/
│   │   └── ingest_tmdb.py       # Main ingestion entry point
│   ├── pipelines/
│   │   ├── fetch_movies.py      # TMDB API fetching logic
│   │   ├── transform.py         # Data cleaning/normalization
│   │   └── load.py              # MongoDB upsert operations
│   ├── tests/
│   │   └── test_pipeline.py
│   ├── requirements.txt
│   └── Dockerfile
├── shared/
│   ├── models.py                # Shared MongoDB document schemas
│   └── config.py                # Shared constants, collection names
├── scripts/
│   └── seed.sh                  # Quick-start helper
├── .env.example
├── docker-compose.yml
└── README.md
```

### Pattern 1: FastAPI Lifespan with AsyncMongoClient
**What:** Use FastAPI's lifespan context manager for MongoDB connection lifecycle
**When to use:** Always -- replaces deprecated `on_event("startup")`/`on_event("shutdown")`
**Example:**
```python
# Source: MongoDB PyMongo docs - FastAPI integration
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create async MongoDB client
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]
    # Create indexes
    await app.state.db.movies.create_index([("title", "text")])
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])
    yield
    # Shutdown: close connection
    app.state.mongo_client.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Pydantic Settings for Configuration
**What:** Type-safe environment variable loading from single `.env` at repo root
**When to use:** All services (backend, worker)
**Example:**
```python
# Source: pydantic-settings docs
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "movie_mrs"
    TMDB_API_KEY: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}

settings = Settings()
```

### Pattern 3: Repository Pattern for MongoDB
**What:** Separate data access from business logic
**When to use:** All MongoDB operations
**Example:**
```python
# movie_repo.py
from pymongo.asynchronous.database import AsyncDatabase

class MovieRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection = db["movies"]

    async def search(self, query: str | None, genre: str | None,
                     year: int | None, skip: int = 0, limit: int = 20):
        filters = {}
        if query:
            filters["$text"] = {"$search": query}
        if genre:
            filters["genres"] = genre
        if year:
            filters["year"] = year

        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_by_tmdb_id(self, tmdb_id: int):
        return await self.collection.find_one({"tmdb_id": tmdb_id})

    async def upsert(self, tmdb_id: int, movie_data: dict):
        await self.collection.update_one(
            {"tmdb_id": tmdb_id},
            {"$set": movie_data},
            upsert=True
        )
```

### Pattern 4: JWT Auth Dependency
**What:** FastAPI dependency for extracting and validating JWT from Bearer header
**When to use:** All protected endpoints
**Example:**
```python
# Source: FastAPI official docs - OAuth2 JWT tutorial
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id
```

### Pattern 5: TMDB Batch Ingestion with Retry
**What:** Paginate TMDB list endpoints, fetch details, upsert to MongoDB
**When to use:** Worker pipeline
**Example:**
```python
# Source: TMDB API docs + tenacity docs
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

TMDB_BASE = "https://api.themoviedb.org/3"

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
)
async def fetch_tmdb(client: httpx.AsyncClient, path: str, params: dict = None):
    resp = await client.get(f"{TMDB_BASE}{path}", params=params)
    resp.raise_for_status()
    return resp.json()

async def ingest_movies(api_key: str, db):
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        seen_ids = set()
        for endpoint in ["/movie/popular", "/movie/top_rated"]:
            page = 1
            while len(seen_ids) < 5000:
                data = await fetch_tmdb(client, endpoint, {"page": page})
                if not data.get("results"):
                    break
                for movie in data["results"]:
                    if movie["id"] in seen_ids:
                        continue
                    seen_ids.add(movie["id"])
                    # Fetch details + credits + translations
                    details = await fetch_tmdb(client, f"/movie/{movie['id']}",
                                               {"append_to_response": "credits,translations"})
                    movie_doc = transform_movie(details)
                    await db.movies.update_one(
                        {"tmdb_id": movie["id"]},
                        {"$set": movie_doc},
                        upsert=True
                    )
                page += 1
```

### Pattern 6: Axios Instance with JWT Interceptor
**What:** Centralized API client that injects auth token
**When to use:** All frontend API calls
**Example:**
```typescript
// src/lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

### Anti-Patterns to Avoid
- **Motor for new projects:** Motor is deprecated (May 2025). Use PyMongo `AsyncMongoClient` directly.
- **Storing JWT in cookies without CSRF protection:** For this SPA, `localStorage` is acceptable given the auth is intentionally minimal. Do not use httpOnly cookies without CSRF tokens.
- **Synchronous TMDB calls in worker:** Even in a batch worker, use async `httpx` to parallelize API calls and finish well within the 2-hour limit.
- **No indexes on search fields:** Without a text index on `title` and compound index on `genres`+`year`, search will table-scan and exceed the 2-second SLA.
- **Hardcoded TMDB API key:** Always load from `.env` via pydantic-settings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop with sleep | `tenacity` library | Handles jitter, max attempts, exception filtering, logging |
| Password hashing | Raw bcrypt calls | `passlib.context.CryptContext` | Handles algorithm upgrades, deprecated scheme migration |
| JWT creation/validation | Manual base64 encoding | `python-jose` | Handles expiry, algorithm verification, standard claims |
| Form data parsing | Manual request body parsing | `python-multipart` + Pydantic | FastAPI handles validation automatically |
| Debounced search | Raw setTimeout/clearTimeout | `useDebouncedValue` hook (custom, ~5 lines) or lodash.debounce | Easy to get wrong with race conditions |
| Data fetching + caching | Custom fetch + useState | `@tanstack/react-query` | Handles loading, error, cache invalidation, refetch |
| Environment config | `os.getenv()` calls | `pydantic-settings` | Type validation, `.env` file support, defaults |

**Key insight:** This phase is infrastructure. Every hour spent hand-rolling solved problems is an hour not spent on the recommendation engine (Phase 2), which is what the capstone is graded on.

## Common Pitfalls

### Pitfall 1: Motor Instead of PyMongo Async
**What goes wrong:** Using Motor for a new project in 2026 means building on a deprecated library
**Why it happens:** Many tutorials and Stack Overflow answers still reference Motor
**How to avoid:** Use `from pymongo import AsyncMongoClient` directly. The API is nearly identical.
**Warning signs:** Any import from `motor.motor_asyncio`

### Pitfall 2: TMDB `append_to_response` Not Used
**What goes wrong:** Making separate API calls for details, credits, and translations = 3x the requests
**Why it happens:** Not reading TMDB docs carefully
**How to avoid:** Use `append_to_response=credits,translations` on the `/movie/{id}` endpoint to get everything in one call. This reduces ~15,000 calls to ~5,500.
**Warning signs:** Separate calls to `/movie/{id}/credits` and `/movie/{id}/translations`

### Pitfall 3: No MongoDB Text Index Before Search
**What goes wrong:** Full collection scan on every search query; 2-second SLA violated
**Why it happens:** Forgetting to create indexes at app startup or in migration script
**How to avoid:** Create text index on `title` (and optionally `overview`) in FastAPI lifespan startup. Also create compound index on `genres` + `year`.
**Warning signs:** Slow search responses, MongoDB `COLLSCAN` in explain plans

### Pitfall 4: Missing Fields Crash the Pipeline
**What goes wrong:** TMDB returns `null` for some fields (e.g., `overview`, `poster_path`); pipeline crashes with KeyError or validation error
**Why it happens:** Assuming all TMDB responses have complete data
**How to avoid:** Use Pydantic models with `Optional[str] = None` for all nullable fields. Use `.get()` for dict access in transform logic.
**Warning signs:** Unhandled exceptions during batch ingestion

### Pitfall 5: CORS Not Configured
**What goes wrong:** Frontend cannot reach backend API; browser blocks requests
**Why it happens:** FastAPI doesn't enable CORS by default
**How to avoid:** Add `CORSMiddleware` in `main.py` allowing the frontend origin (or `*` for development)
**Warning signs:** Browser console shows "CORS policy" errors

### Pitfall 6: Docker Compose MongoDB Networking
**What goes wrong:** Backend/worker cannot connect to MongoDB container
**Why it happens:** Using `localhost` instead of Docker service name in connection string
**How to avoid:** Use service name (e.g., `mongodb://mongo:27017/movie_mrs`) in Docker, with `.env` override for local development
**Warning signs:** Connection refused errors when running in Docker

### Pitfall 7: JWT Secret Too Short or Predictable
**What goes wrong:** Tokens can be forged
**Why it happens:** Using simple strings like "secret" during development and forgetting to change
**How to avoid:** Generate with `openssl rand -hex 32` and put in `.env`. Provide example in `.env.example`.
**Warning signs:** JWT_SECRET shorter than 32 characters

## Code Examples

### MongoDB Movie Document Schema
```python
# Source: Project requirements + TMDB API response structure
# shared/models.py
from datetime import datetime
from typing import Optional

movie_schema = {
    "tmdb_id": int,           # TMDB movie ID (unique key for upsert)
    "title": str,              # Original English title
    "title_tr": Optional[str], # Turkish title from translations
    "year": Optional[int],     # Release year extracted from release_date
    "genres": list[str],       # Genre names (not IDs)
    "overview": Optional[str], # Plot summary
    "poster_path": Optional[str],  # TMDB poster path (prepend base URL)
    "rating": Optional[float],     # vote_average
    "vote_count": Optional[int],
    "popularity": Optional[float],
    "director": Optional[str],     # From credits crew (job == "Director")
    "cast": list[str],             # Top 5 cast member names
    "ingested_at": datetime,       # Timestamp of last ingestion
}

user_schema = {
    "email": str,              # Unique, used as login identifier
    "hashed_password": str,    # bcrypt hash
    "display_name": Optional[str],
    "created_at": datetime,
}
```

### TMDB Data Transform
```python
# worker/pipelines/transform.py
def transform_movie(tmdb_data: dict) -> dict:
    """Transform TMDB API response into our movie document format."""
    # Extract director from crew
    credits = tmdb_data.get("credits", {})
    crew = credits.get("crew", [])
    director = next((p["name"] for p in crew if p.get("job") == "Director"), None)

    # Extract top 5 cast
    cast_list = credits.get("cast", [])
    cast = [p["name"] for p in cast_list[:5]]

    # Extract Turkish title
    translations = tmdb_data.get("translations", {}).get("translations", [])
    title_tr = None
    for t in translations:
        if t.get("iso_639_1") == "tr":
            title_tr = t.get("data", {}).get("title")
            break

    # Extract year from release_date
    release_date = tmdb_data.get("release_date", "")
    year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    # Extract genre names
    genres = [g["name"] for g in tmdb_data.get("genres", [])]

    return {
        "tmdb_id": tmdb_data["id"],
        "title": tmdb_data.get("title", "Unknown"),
        "title_tr": title_tr,
        "year": year,
        "genres": genres,
        "overview": tmdb_data.get("overview"),
        "poster_path": tmdb_data.get("poster_path"),
        "rating": tmdb_data.get("vote_average"),
        "vote_count": tmdb_data.get("vote_count"),
        "popularity": tmdb_data.get("popularity"),
        "director": director,
        "cast": cast,
    }
```

### Debounced Search Hook
```typescript
// src/hooks/useMovies.ts
import { useQuery } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import api from '../lib/api';

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function useMovieSearch(query: string, genre: string, year: string) {
  const debouncedQuery = useDebouncedValue(query, 300);

  return useQuery({
    queryKey: ['movies', 'search', debouncedQuery, genre, year],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedQuery) params.set('q', debouncedQuery);
      if (genre) params.set('genre', genre);
      if (year) params.set('year', year);
      const { data } = await api.get(`/movies?${params}`);
      return data;
    },
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor for async MongoDB | PyMongo `AsyncMongoClient` | May 2025 (Motor deprecated) | Must use PyMongo async API for new projects |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI ~0.109 | Deprecated event handlers; use lifespan |
| Pydantic v1 models | Pydantic v2 with `model_config` | 2023+ | FastAPI fully supports v2; use `model_config` not `class Config` |
| `create-react-app` | Vite | 2023+ | CRA is unmaintained; Vite is the standard |
| Tailwind CSS v3 | Tailwind CSS v4 | Early 2025 | New configuration approach; v4 is current |
| React Router v6 | React Router v7 | Late 2024 | v7 is stable; non-breaking upgrade from v6 |

**Deprecated/outdated:**
- **Motor:** Deprecated May 14, 2025. EOL May 14, 2026. Use PyMongo async.
- **`@app.on_event`:** Deprecated in FastAPI. Use `lifespan` context manager.
- **Pydantic v1 `class Config`:** Use `model_config = {...}` dict in Pydantic v2.

## Open Questions

1. **TMDB API Key Availability**
   - What we know: Key not yet obtained (noted in STATE.md blockers)
   - What's unclear: Whether Cenk has applied for the key
   - Recommendation: Block DATA-01/DATA-02 tasks on API key availability; scaffold and test with mock data first

2. **MongoDB Atlas Free Tier Limits**
   - What we know: 512 MB storage limit on M0 free tier
   - What's unclear: Whether 5,000 movie documents with full metadata exceeds this
   - Recommendation: Estimate ~1-2 KB per document = ~5-10 MB total. Well within 512 MB. No concern.

3. **TMDB `append_to_response` with Translations**
   - What we know: `append_to_response` supports `credits` and `translations` in a single call
   - What's unclear: Whether there are any rate-limit differences for appended resources
   - Recommendation: Test with a small batch first; if issues arise, fall back to separate calls for translations only

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ~8.x + pytest-asyncio ~0.24+ (backend/worker), vitest ~3.x (frontend) |
| Config file | `backend/pytest.ini` or `pyproject.toml` (Wave 0), `frontend/vitest.config.ts` (Wave 0) |
| Quick run command | `cd backend && pytest tests/ -x --timeout=30` |
| Full suite command | `cd backend && pytest tests/ -v && cd ../worker && pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | TMDB metadata ingested correctly | unit | `pytest worker/tests/test_pipeline.py::test_transform_movie -x` | Wave 0 |
| DATA-02 | Turkish title extracted from translations | unit | `pytest worker/tests/test_pipeline.py::test_turkish_title -x` | Wave 0 |
| DATA-04 | Missing fields handled gracefully | unit | `pytest worker/tests/test_pipeline.py::test_missing_fields -x` | Wave 0 |
| DATA-05 | Batch pipeline runs end-to-end | integration | `pytest worker/tests/test_pipeline.py::test_ingestion_e2e -x` | Wave 0 |
| DATA-06 | Pipeline completes within 2h | manual-only | Manual timing of full ingestion run | N/A |
| UI-01 | User can register and login | e2e | Manual or Playwright (future) | Wave 0 |
| UI-03 | Search with filters works | e2e | Manual or Playwright (future) | Wave 0 |
| API-01 | Movie listing/search/filter endpoints | unit | `pytest backend/tests/test_movies.py -x` | Wave 0 |
| API-04 | TMDB retry on failure | unit | `pytest worker/tests/test_pipeline.py::test_retry_on_failure -x` | Wave 0 |
| API-06 | Search responds < 2s | integration | `pytest backend/tests/test_movies.py::test_search_performance -x` | Wave 0 |
| SEC-01 | Data persisted in MongoDB | integration | `pytest backend/tests/test_movies.py::test_persistence -x` | Wave 0 |
| SEC-02 | Passwords bcrypt hashed | unit | `pytest backend/tests/test_auth.py::test_password_hashing -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/ -x --timeout=30`
- **Per wave merge:** `cd backend && pytest tests/ -v && cd ../worker && pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/pytest.ini` or `backend/pyproject.toml` -- pytest configuration with asyncio mode
- [ ] `backend/tests/conftest.py` -- shared fixtures (test DB, test client, mock TMDB)
- [ ] `backend/tests/test_auth.py` -- covers SEC-02, UI-01 API side
- [ ] `backend/tests/test_movies.py` -- covers API-01, API-06, SEC-01
- [ ] `worker/tests/conftest.py` -- shared fixtures (mock TMDB responses, test DB)
- [ ] `worker/tests/test_pipeline.py` -- covers DATA-01, DATA-02, DATA-04, DATA-05, API-04
- [ ] `frontend/vitest.config.ts` -- vitest configuration
- [ ] Framework installs: `pip install pytest pytest-asyncio` (backend/worker), `npm install -D vitest` (frontend)

## Sources

### Primary (HIGH confidence)
- [MongoDB PyMongo FastAPI Integration Tutorial](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/integrations/fastapi-integration/) -- AsyncMongoClient + lifespan pattern
- [FastAPI OAuth2 JWT Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) -- JWT auth with python-jose and passlib
- [TMDB API Rate Limiting](https://developer.themoviedb.org/docs/rate-limiting) -- ~40 req/s soft limit, 429 error handling
- [PyMongo Motor Migration Guide](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/) -- Motor deprecated May 2025, use PyMongo async
- [MongoDB Best Practices for FastAPI](https://www.mongodb.com/developer/products/mongodb/8-fastapi-mongodb-best-practices/) -- Connection management, indexing, error handling
- [shadcn/ui Vite Installation](https://ui.shadcn.com/docs/installation/vite) -- React + Vite + Tailwind + shadcn setup

### Secondary (MEDIUM confidence)
- [FastAPI Testing Strategies](https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/) -- pytest + httpx AsyncClient testing patterns
- [TMDB API Getting Started](https://developer.themoviedb.org/docs/getting-started) -- API v3 endpoint structure
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) -- v2.13.1 latest as of Feb 2026

### Tertiary (LOW confidence)
- TMDB forum discussions on rate limits -- exact per-second thresholds vary and are intentionally undocumented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified current, versions checked against PyPI/npm
- Architecture: HIGH -- patterns from official MongoDB and FastAPI documentation
- Pitfalls: HIGH -- based on official deprecation notices and documented migration paths
- TMDB specifics: MEDIUM -- rate limits intentionally vague; `append_to_response` for translations needs runtime validation

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable ecosystem, no major releases expected)
