# Phase 3: Collaborative Filtering and Hybrid Engine - Research

**Researched:** 2026-03-26
**Domain:** Item-based CF, hybrid blending, rate limiting, feedback UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Like/dislike buttons appear below each MovieCard, next to the explanation text (same row)
- Controls are on the `/recommendations` page only — not on the movie detail page
- Visual state: clicked button highlights/fills with color; user can change vote by clicking the other button (like after dislike replaces the interaction)
- Optimistic update — no page reload needed after feedback
- API: binary only (`like` | `dislike`); clicking the other button replaces the previous interaction (no un-vote/delete logic needed)
- `POST /api/feedback` — accepts `{ movie_id: int, action: "like" | "dislike" }`
- Authenticated endpoint (JWT required)
- Upserts interaction in MongoDB — same movie can only have one interaction per user
- **Item-based CF** — pre-compute a user–movie interaction matrix; find movies liked by users who liked the same movies as the current user
- No neural network (PyTorch NCF explicitly off the table)
- Runs as an **offline batch job** in the worker (same pattern as `nlp_features.py`) — reads all interactions from MongoDB, computes CF score matrix, writes artifact to disk
- API loads both NLP artifact and CF artifact at startup; CF scores are served from memory at request time
- If no CF artifact exists at startup → fall back silently to pure content-based (`alpha = 1.0`)
- Use **MovieLens-20M** interactions mapped to TMDB IDs via `links.csv` (direct `tmdbId` column, no fuzzy matching)
- Ingest a subset of MovieLens ratings (threshold ≥ 4.0 → "like", ≤ 2.0 → "dislike") as synthetic interactions
- A seeding script (`worker/jobs/seed_interactions.py`) handles the import
- **Step function at threshold:** if `interaction_count < 5` → `alpha = 1.0` (pure content); if `≥ 5` → `alpha = 0.5` (equal blend)
- Threshold (5) and collaborative weight (0.5) are **env-configurable** (`CF_THRESHOLD`, `CF_ALPHA`)
- **Score formula:** `hybrid_score = alpha * norm(content_score) + (1 - alpha) * norm(cf_score)`
- Both scores normalized to [0, 1] before blending: `norm(x) = (x - min) / (max - min)` across the candidate set for that request
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

### Deferred Ideas (OUT OF SCOPE)
- REC-06: Dynamic alpha beyond the step function (smooth ramp, sigmoid) — v2
- Redis-based rate limiting for multi-server deployment — v2
- Like/dislike on the movie detail page — deferred; recommendations page only for v1
- PyTorch NCF — explicitly deferred; not appropriate for this timeline and data volume
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-03 | System stores user interactions (like/dislike per movie) | `interactions` MongoDB collection, upsert pattern from `UserPreferencesRepository` |
| REC-03 | System implements collaborative filtering signal from user interactions | Item-based CF via scipy sparse user-item matrix + cosine similarity, joblib artifact |
| REC-04 | System combines content-based and collaborative signals using hybrid weighted scoring | Step-function alpha, min-max norm, hybrid formula in `RecommendationService.get_recommendations()` |
| UI-05 | User can provide like/dislike feedback on recommended movies | `useFeedback` mutation hook, optimistic state update via TanStack Query `useMutation` |
| API-03 | System exposes REST endpoint for user feedback submission | `POST /api/feedback` router following existing recommendations router pattern |
| API-07 | System supports at least 10 concurrent users | slowapi in-memory rate limiting + existing async FastAPI architecture handles concurrency |
| SEC-03 | System applies rate limiting (10 requests/minute/user) on recommendation endpoints | slowapi 0.1.9 with custom JWT key_func on `POST /api/recommendations` |
</phase_requirements>

---

## Summary

Phase 3 layers collaborative filtering and hybrid blending on top of the existing content-based engine without modifying Phase 2 code. The approach — item-based CF computed offline as a batch job — is the correct choice for this codebase: it mirrors the existing `nlp_features.py` pattern exactly, produces a joblib artifact the API loads at startup, and requires no GPU or additional infrastructure.

The MovieLens-20M dataset provides 20 million ratings across ~27,000 movies. The `links.csv` file contains a direct `tmdbId` column, enabling exact ID-to-TMDB mapping without fuzzy matching. A subset of ratings (≥ 4.0 → like, ≤ 2.0 → dislike) from a bounded number of MovieLens users provides realistic collaborative signal even before real users provide feedback.

Rate limiting via slowapi 0.1.9 is the standard FastAPI-native solution: three lines of setup code, a custom JWT-based `key_func`, and a decorator on the target endpoint. The full implementation — CF worker job, feedback API, hybrid blending, rate limiter, UI — slots into the existing architecture with no new infrastructure.

**Primary recommendation:** Follow the established offline-batch-to-joblib-artifact pattern for CF, add slowapi as a new backend dependency, and use TanStack Query `useMutation` with optimistic UI state for feedback buttons.

---

## Standard Stack

### Core (all already present except slowapi)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scipy | ≥1.17.0 | `csr_matrix` for sparse user-item matrix | Already in worker/requirements.txt; sparse format essential for large interaction matrices |
| scikit-learn | ≥1.6.0,<2.0.0 | `cosine_similarity` for item-item CF scores | Already present; identical API to NLP pipeline usage |
| joblib | ≥1.3.0 | Artifact serialization for CF matrix | Already present; matches NLP artifact pattern |
| numpy | ≥2.0.0 | Score normalization, array operations | Already present |
| slowapi | 0.1.9 | Rate limiting for FastAPI | De-facto standard for FastAPI rate limiting; no Redis needed for in-memory |
| TanStack Query (`@tanstack/react-query`) | Already installed | `useMutation` for optimistic feedback UI | Already used by `useRecommendations` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| limits (slowapi dep) | ≥2.3 | Sliding window storage backend | Pulled in automatically by slowapi; no direct usage needed |
| pandas | any | Optional: loading `links.csv` in seed script | Only in seed script; `csv.reader` works too and avoids a dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scipy csr_matrix | dense numpy array | Dense would use ~400 MB for 5k movies × 10k users; sparse uses ~5-20 MB for typical 1% fill rate |
| slowapi 0.1.9 | fastapi-limiter | fastapi-limiter requires Redis; slowapi is in-memory, matches "no new infrastructure" constraint |
| TanStack useMutation | direct axios call + useState | useMutation provides isPending/isError states, onSuccess/onError callbacks, and cache invalidation for free |

**Installation (backend):**
```bash
pip install slowapi==0.1.9
```

**Version verification (confirmed 2026-03-26):**
- slowapi: 0.1.9 (latest — PyPI confirmed)
- scipy: ≥1.17.0 already in worker/requirements.txt
- scikit-learn, numpy, joblib: already pinned in both requirements files

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
worker/jobs/
├── cf_features.py          # Offline batch: reads interactions → computes item-item CF scores → saves artifact
├── seed_interactions.py    # One-time: loads MovieLens links.csv + ratings.csv → writes to MongoDB interactions collection

backend/app/
├── api/routes/
│   └── feedback.py         # POST /api/feedback router
├── repositories/
│   └── interactions_repo.py  # CRUD for MongoDB interactions collection
└── services/
    └── recommendation_service.py  # MODIFIED: add hybrid blending

shared/
└── config.py               # MODIFIED: add INTERACTIONS_COLLECTION constant

frontend/src/
├── hooks/
│   └── useFeedback.ts      # useMutation hook for POST /api/feedback
└── pages/
    └── RecommendationsPage.tsx  # MODIFIED: add like/dislike buttons per card
```

### Pattern 1: Item-Based CF Batch Job (mirrors nlp_features.py)

**What:** Read all interaction documents from MongoDB, build a sparse user-item matrix (scipy csr_matrix), compute item-item cosine similarity, extract top-N CF neighbors per movie, save as joblib artifact.

**When to use:** Every time new interaction data is available; run after seeding or when interaction count crosses a meaningful threshold.

**Matrix dimensions for this project:**
- Seeded interactions: subset of MovieLens-20M filtered to movies with TMDB IDs present in our `movies` collection. With 5,000 movies and a reasonable subset (e.g., 10,000 synthetic users), the user-item matrix is 10,000 × 5,000 = very sparse (~0.1–1% fill). Use `scipy.sparse.csr_matrix`.
- CF artifact: dict with `{"tmdb_ids": list[int], "cf_top_indices": np.ndarray[shape=(N_movies, top_n), dtype=int32]}` — same structure as the NLP `similarity_index.joblib`.

```python
# Source: scipy docs + nlp_features.py pattern
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
import joblib

def build_cf_index(interactions: list[dict], tmdb_ids: list[int], top_n: int = 50) -> np.ndarray:
    """Build item-item CF similarity index from user interactions.

    Args:
        interactions: List of {"user_id": str, "movie_id": int, "action": "like"|"dislike"} dicts
        tmdb_ids: Ordered list of TMDB IDs (same order as NLP artifact)
        top_n: Number of CF neighbors per movie

    Returns:
        np.ndarray of shape (N_movies, min(top_n, N-1)), dtype int32
    """
    tmdb_to_idx = {tid: i for i, tid in enumerate(tmdb_ids)}
    # Assign sequential integer IDs to users
    user_ids = list({ia["user_id"] for ia in interactions})
    user_to_idx = {uid: i for i, uid in enumerate(user_ids)}

    N_users = len(user_ids)
    N_movies = len(tmdb_ids)

    rows, cols, data = [], [], []
    for ia in interactions:
        movie_idx = tmdb_to_idx.get(ia["movie_id"])
        user_idx = user_to_idx.get(ia["user_id"])
        if movie_idx is None or user_idx is None:
            continue
        score = 1.0 if ia["action"] == "like" else -1.0
        rows.append(user_idx)
        cols.append(movie_idx)
        data.append(score)

    user_item = csr_matrix((data, (rows, cols)), shape=(N_users, N_movies))

    # item-item similarity: transpose → shape (N_movies, N_users)
    # cosine_similarity on item vectors
    effective_top_n = min(top_n, N_movies - 1)
    cf_top_indices = np.zeros((N_movies, effective_top_n), dtype=np.int32)
    item_matrix = user_item.T  # shape (N_movies, N_users)

    for i in range(N_movies):
        sims = cosine_similarity(item_matrix[i], item_matrix).flatten()
        sims[i] = -1.0  # exclude self
        cf_top_indices[i] = np.argpartition(sims, -effective_top_n)[-effective_top_n:]

    return cf_top_indices
```

### Pattern 2: Hybrid Blending in RecommendationService

**What:** After computing `candidate_scores` (content-based, existing logic), query CF artifact for additional CF candidate scores, normalize both to [0,1], blend by alpha, re-rank.

**When to use:** Every recommendation request for authenticated users with CF artifact loaded.

```python
# Source: CONTEXT.md formula + existing recommendation_service.py pattern

def _norm(scores: dict[int, float]) -> dict[int, float]:
    """Min-max normalize a score dict to [0, 1].

    Edge case: if max == min (all scores identical), return 0.5 for all.
    This prevents division-by-zero and keeps candidates in the pool.
    """
    if not scores:
        return scores
    min_s = min(scores.values())
    max_s = max(scores.values())
    if max_s == min_s:
        return {k: 0.5 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


def _get_alpha(interaction_count: int, threshold: int, cf_alpha: float) -> float:
    """Step function: pure content below threshold, blend at/above."""
    if interaction_count >= threshold:
        return 1.0 - cf_alpha  # weight given to CF; content weight = cf_alpha
    return 1.0  # pure content (alpha=1.0 means no CF weight)


# In get_recommendations():
# alpha = 1.0 → hybrid_score = 1.0 * norm(content) + 0.0 * norm(cf)
# alpha = 0.5 → hybrid_score = 0.5 * norm(content) + 0.5 * norm(cf)
# Formula: hybrid_score = alpha * norm(content) + (1 - alpha) * norm(cf)
```

**Integration point in `get_recommendations()`:**
1. Compute `candidate_scores` (existing content logic, unchanged)
2. If `app_state.cf_top_indices` is not None AND `interaction_count >= CF_THRESHOLD`:
   - Look up user's liked movies → find their CF neighbors → build `cf_scores` dict
   - Normalize both dicts with `_norm()`
   - Blend: `hybrid = alpha * norm_content[tid] + (1-alpha) * norm_cf.get(tid, 0.0)` for each candidate
3. Else: rank by content scores only

### Pattern 3: slowapi Rate Limiting

**What:** Add slowapi middleware to FastAPI app, define a JWT-based key function, decorate `POST /api/recommendations` endpoint.

**Critical requirement:** The endpoint function MUST receive `request: Request` as a parameter for slowapi to hook in. The existing `get_recommendations` endpoint does NOT currently have this parameter — it must be added.

```python
# Source: slowapi 0.1.9 docs pattern

# In backend/app/main.py (additions)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

def _get_user_id_or_ip(request: Request) -> str:
    """Key function: use JWT sub claim if authenticated, else fall back to client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            from jose import jwt, JWTError
            from app.core.config import settings
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return request.client.host  # fallback for unauthenticated

limiter = Limiter(key_func=_get_user_id_or_ip)

# In app creation:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# In the recommendations router:
from app.main import limiter  # or pass via app.state

@router.post("", response_model=RecommendationResponse)
@limiter.limit("10/minute")
async def get_recommendations(
    request: Request,   # ← MUST be present for slowapi to work
    body: PreferenceRequest,
    service: RecommendationService = Depends(_get_recommendation_service),
    user_id: str | None = Depends(_get_optional_user),
) -> RecommendationResponse:
    ...
```

**Response on limit exceeded:** slowapi's `_rate_limit_exceeded_handler` automatically returns HTTP 429 with `Retry-After` header. No custom handler needed.

**Limiter access in routers:** The cleanest pattern is to define `limiter` at module level in `main.py`, then import it in the router file. Alternatively, access via `request.app.state.limiter`.

### Pattern 4: TanStack Query useMutation for Feedback

**What:** A `useFeedback` hook that sends `POST /api/feedback` and updates local optimistic state.

**Key insight:** Use the "UI variables" optimistic pattern (simpler than cache invalidation): store the current vote in component state, update it immediately on click, then fire the mutation. On error, revert to previous state.

```typescript
// Source: TanStack Query useMutation docs + useRecommendations.ts pattern

import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';
import type { FeedbackAction } from '../lib/types';

interface FeedbackPayload {
  movie_id: number;
  action: FeedbackAction;
}

export function useFeedback() {
  return useMutation<void, Error, FeedbackPayload>({
    mutationFn: async (payload) => {
      await api.post('/feedback', payload);
    },
  });
}
```

**Component usage in RecommendationsPage.tsx (around line 241):**
```typescript
// Per-card state: Map<tmdb_id, FeedbackAction | null>
const [votes, setVotes] = useState<Map<number, FeedbackAction | null>>(new Map());
const { mutate: submitFeedback } = useFeedback();

function handleVote(tmdbId: number, action: FeedbackAction) {
  const prev = votes.get(tmdbId) ?? null;
  // Optimistic update: set immediately
  setVotes((m) => new Map(m).set(tmdbId, action));
  submitFeedback(
    { movie_id: tmdbId, action },
    {
      onError: () => {
        // Revert on failure
        setVotes((m) => new Map(m).set(tmdbId, prev));
      },
    }
  );
}
```

### Pattern 5: InteractionsRepository (mirrors UserPreferencesRepository)

```python
# Source: backend/app/repositories/user_preferences_repo.py pattern

class InteractionsRepository:
    def __init__(self, db) -> None:
        self.collection = db[INTERACTIONS_COLLECTION]  # "interactions"

    async def upsert(self, user_id: str, movie_id: int, action: str) -> None:
        """Insert or replace interaction for (user_id, movie_id) pair."""
        await self.collection.update_one(
            {"user_id": user_id, "movie_id": movie_id},
            {"$set": {
                "user_id": user_id,
                "movie_id": movie_id,
                "action": action,
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    async def get_by_user_id(self, user_id: str) -> list[dict]:
        """Return all interaction documents for a user."""
        cursor = self.collection.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def count_by_user_id(self, user_id: str) -> int:
        """Return total interaction count for a user (used for alpha threshold check)."""
        return await self.collection.count_documents({"user_id": user_id})
```

**MongoDB index needed:** Compound index on `(user_id, movie_id)` for fast upsert lookups. Create in lifespan alongside existing indexes.

### Pattern 6: MovieLens Seeding Script

**What:** `worker/jobs/seed_interactions.py` — reads `links.csv` + `ratings.csv`, filters to movies present in MongoDB's `movies` collection, creates synthetic user documents with sequential IDs (`seed_user_0`, `seed_user_1`, ...), inserts interactions into the `interactions` collection.

**Key implementation details:**
- `links.csv` columns: `movieId,imdbId,tmdbId` — use `tmdbId` for direct mapping
- `ratings.csv` columns: `userId,movieId,rating,timestamp` — filter by `rating >= 4.0` (like) or `rating <= 2.0` (dislike)
- `tmdbId` values in links.csv may have NaN entries (not all MovieLens movies map to TMDB) — skip rows where `tmdbId` is empty
- Scope the seed to a manageable user count (e.g., 500–2,000 users) to keep the CF batch job fast
- The script is idempotent: clear existing seed users' interactions before reinserting

```python
# Pseudocode pattern (follows ingest_tmdb.py structure)
async def main():
    load_dotenv(...)
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    # Load links.csv → build movieId → tmdbId mapping
    # Load ratings.csv → filter to ≥4.0 or ≤2.0
    # Find movies that exist in DB: {tmdb_id: {"$in": list(tmdb_ids_from_links)}}
    # For each rating that maps to a valid TMDB ID: upsert interaction
    # Use user_id = f"seed_user_{userId}" to namespace synthetic users
```

### Anti-Patterns to Avoid

- **Dense item-item matrix:** `cosine_similarity(item_matrix_T)` on a 5,000 × 5,000 dense matrix = 200 MB float64. Use the same row-by-row loop from `nlp_features.py` or `NearestNeighbors` for top-K only.
- **CF artifact with no fallback guard:** If `cf_top_indices` is None (artifact missing), the hybrid blending must silently use `alpha = 1.0`. Never raise a 503.
- **limiter as a global import from main.py:** Creates circular import risk. Better to store on `app.state.limiter` and access it in routes via `request.app.state.limiter`, or define it in a separate `app/core/limiter.py` module.
- **norm() division by zero:** When all candidate scores are identical (e.g., first request for a genre with few matches), `max - min = 0`. Always return 0.5 for all candidates in this case (keeps them in pool, preserves tie-breaking by content order).
- **Passing `request: Request` to a Depends function instead of the endpoint:** slowapi requires `request` as a direct parameter of the decorated function, not buried inside a dependency. The existing `get_recommendations` endpoint needs `request: Request` added as an explicit parameter.
- **Seeding too many users:** MovieLens-20M has 138,000 users. Seeding all of them would create ~100k interaction documents before any real user data. Limit to a representative subset (1,000–5,000 users covering the movies in your DB).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sparse matrix operations | Custom dict-of-dicts interaction store | `scipy.sparse.csr_matrix` | Handles sparsity efficiently; enables fast matrix multiply for cosine similarity |
| Cosine similarity | Manual dot product / magnitude calculation | `sklearn.metrics.pairwise.cosine_similarity` | Already used in NLP pipeline; handles sparse input; numerically stable |
| Artifact serialization | pickle or custom binary format | `joblib.dump/load` | Already used for NLP artifacts; handles numpy arrays efficiently; consistent pattern |
| Rate limiting | Token bucket implementation in middleware | `slowapi==0.1.9` | 429 + Retry-After, in-memory storage, JWT key_func support — 5 lines of setup |
| Optimistic UI updates | Manual loading state + refetch logic | TanStack Query `useMutation` with `onError` rollback | Already in project; handles pending/error/success states; cache invalidation built-in |

**Key insight:** The CF computation is structurally identical to the NLP similarity pipeline already written. The same `argpartition`-based top-N extraction, same joblib persistence, same `app_state` loading pattern. Build CF as a parallel artifact to NLP — don't design a new pattern.

---

## Common Pitfalls

### Pitfall 1: slowapi `request` parameter missing from endpoint
**What goes wrong:** `AttributeError: 'Request' object has no attribute 'app'` or rate limiter silently skips — requests never get counted.
**Why it happens:** slowapi hooks into the ASGI request object. If `request: Request` is not an explicit parameter of the decorated function, the library cannot find it.
**How to avoid:** Always add `request: Request` as the first parameter of any endpoint decorated with `@limiter.limit()`. The existing `get_recommendations` function does not have this — it must be added.
**Warning signs:** Rate limiting "works" (no error) but requests are never throttled; logs show no rate limit hits.

### Pitfall 2: CF artifact missing at startup causes 503
**What goes wrong:** API raises 503 for all recommendation requests before the CF batch job has run.
**Why it happens:** If `app_state.cf_top_indices` check is mixed with the NLP artifact check, a missing CF artifact could propagate the 503.
**How to avoid:** Load CF artifact in a separate, independent `if` block in lifespan. Set `app.state.cf_top_indices = None` as the fallback. In `get_recommendations()`, check `cf_top_indices is not None` before attempting hybrid blend.
**Warning signs:** Recommendations endpoint returns 503 after a clean deploy where only NLP artifacts exist.

### Pitfall 3: tmdbId NaN in MovieLens links.csv
**What goes wrong:** `int(nan)` raises ValueError in seed script; or NaN IDs get stored as strings/floats in MongoDB.
**Why it happens:** Not all 27,278 MovieLens movies map to a TMDB ID. The `tmdbId` column has NaN entries.
**How to avoid:** In seed script, skip any row where `tmdbId` is empty/NaN: `if pd.isna(row.tmdbId): continue` or `if not row[2]: continue` with csv.reader.
**Warning signs:** MongoDB interactions collection has documents with `movie_id: NaN` or `movie_id: None`; CF batch job produces all-zero scores for those entries.

### Pitfall 4: CF scores dominate content scores (scale mismatch)
**What goes wrong:** CF scores are in [−1, 1] (cosine of signed interaction vectors); content scores are raw frequency counts. Without normalization, one overwhelms the other.
**Why it happens:** The two scoring systems have different ranges by construction.
**How to avoid:** Always apply `_norm()` to both score dicts before blending, per the locked formula. Verify in tests that normalized scores are in [0, 1].
**Warning signs:** Hybrid recommendations look identical to pure CF (or pure content) regardless of alpha value.

### Pitfall 5: Interaction count query on every recommendation request
**What goes wrong:** Each `POST /api/recommendations` fires a `count_documents` query to determine alpha, adding latency.
**Why it happens:** Naively calling `await interactions_repo.count_by_user_id(user_id)` on every request.
**How to avoid:** The count is inexpensive with a proper index on `user_id`. Create the index in lifespan: `await db.interactions.create_index([("user_id", 1)])`. This keeps the query sub-millisecond.
**Warning signs:** Recommendation endpoint latency spikes after the interactions collection grows to thousands of documents.

### Pitfall 6: mongomock `AsyncCollection` missing `update_one` for interactions
**What goes wrong:** Tests for feedback endpoint fail with AttributeError because `mongomock` doesn't support the full async wrapper surface.
**Why it happens:** `conftest.py` `AsyncCollection` wrapper implements `update_one` — but future tests need to verify the compound-filter upsert pattern works with mongomock.
**How to avoid:** Reuse the existing `AsyncCollection.update_one` — it's already implemented. The compound filter `{"user_id": ..., "movie_id": ...}` works with mongomock's standard filter matching.
**Warning signs:** Upsert tests pass for `user_preferences` but fail for `interactions` despite identical code — check that both keys are in the filter dict.

---

## Code Examples

### CF Artifact Loading in lifespan (main.py extension)

```python
# Source: backend/app/main.py lifespan pattern (existing) + CF extension

# In lifespan, after NLP artifact loading:
cf_index_path = os.path.join(artifacts_dir, "cf_index.joblib")
if os.path.exists(cf_index_path):
    cf_data = joblib.load(cf_index_path)
    app.state.cf_top_indices = cf_data["cf_top_indices"]
    app.state.cf_tmdb_ids = cf_data["tmdb_ids"]  # may differ from NLP if movies differ
    logger.info("CF artifact loaded at startup")
else:
    app.state.cf_top_indices = None
    app.state.cf_tmdb_ids = []
    logger.info("CF artifact not found — hybrid blending disabled until worker runs")
```

### Feedback Router

```python
# Source: backend/app/api/routes/recommendations.py pattern

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.security import get_current_user
from app.core.database import get_db
from app.repositories.interactions_repo import InteractionsRepository

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class FeedbackRequest(BaseModel):
    movie_id: int
    action: str  # "like" | "dislike"

    @field_validator("action")
    @classmethod
    def action_must_be_binary(cls, v):
        if v not in ("like", "dislike"):
            raise ValueError("action must be 'like' or 'dislike'")
        return v

@router.post("", status_code=204)
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
) -> None:
    repo = InteractionsRepository(db)
    await repo.upsert(user_id, body.movie_id, body.action)
```

### MongoDB Index Creation (lifespan addition)

```python
# Compound index for fast (user_id, movie_id) upsert lookups
await app.state.db.interactions.create_index(
    [("user_id", 1), ("movie_id", 1)],
    unique=True,
)
# Single-key index for count_documents by user_id
await app.state.db.interactions.create_index([("user_id", 1)])
```

### FeedbackAction Type (types.ts extension)

```typescript
// Source: frontend/src/lib/types.ts extension

export type FeedbackAction = "like" | "dislike";

export interface UserInteraction {
  movie_id: number;
  action: FeedbackAction;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor (async MongoDB driver) | PyMongo AsyncMongoClient directly | May 2025 (Motor EOL May 2026) | Already in use; do NOT introduce Motor for interactions repo |
| flask-limiter | slowapi (Flask-limiter port for FastAPI) | 2020+ | slowapi is the de-facto standard; no behavior change, just FastAPI-native |
| `@pytest.mark.asyncio` on every test | `asyncio_mode = auto` in pytest.ini | Phase 1 decision | Worker and backend both have this set; new CF/feedback tests need no decorator |
| Dense similarity matrix | Row-by-row sparse computation | Phase 2 implementation | Already established; CF job must follow the same pattern |

**Deprecated/outdated:**
- Motor: deprecated May 2025, EOL May 2026 — confirmed in STATE.md; do not use for `interactions_repo.py`
- `@pytest.mark.asyncio` decorator: redundant; `asyncio_mode=auto` is active in both `worker/pytest.ini` and `backend/pyproject.toml`
- Tailwind `@tailwind` directives: replaced by `@import "tailwindcss"` in this project (v4 setup from STATE.md)

---

## Open Questions

1. **MovieLens-20M tmdbId coverage percentage**
   - What we know: `links.csv` has `tmdbId` column; NaN entries exist for some movies
   - What's unclear: How many of the ~27k MovieLens movies map to TMDB IDs that exist in our 5k-movie corpus
   - Recommendation: Run the seed script with a validation pass first — log "X of Y MovieLens movies matched TMDB IDs in our corpus" before inserting. Expect 60–80% match rate based on dataset overlap patterns (MEDIUM confidence).

2. **limiter import pattern (circular import risk)**
   - What we know: slowapi examples define `limiter` at app level; routers import from app
   - What's unclear: Whether `from app.main import limiter` creates a circular import in this project's structure
   - Recommendation: Define `limiter` in a new `backend/app/core/limiter.py` module; import in both `main.py` (for `app.state.limiter` and exception handler) and the recommendations router. This is the cleanest pattern.

3. **CF batch job trigger mechanism**
   - What we know: The job is offline batch, identical pattern to `nlp_features.py`
   - What's unclear: Whether Phase 3 should add a scheduler (cron, APScheduler) or just document manual re-run
   - Recommendation: Manual `python jobs/cf_features.py` for v1, matching Phase 2 convention. No scheduler needed for capstone scope.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8.0.0 + pytest-asyncio ≥0.24.0 |
| Config file (backend) | `backend/pyproject.toml` — `asyncio_mode = "auto"` |
| Config file (worker) | `worker/pytest.ini` — `asyncio_mode = auto` |
| Quick run command (backend) | `cd backend && pytest tests/ -x -q` |
| Quick run command (worker) | `cd worker && pytest tests/ -x -q` |
| Full suite command | `cd backend && pytest tests/ && cd ../worker && pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-03 | Interactions upserted in MongoDB; same movie overwrites previous action | unit | `cd backend && pytest tests/test_feedback.py -x` | ❌ Wave 0 |
| REC-03 | CF batch job builds artifact; top-N indices correct shape; excludes self | unit | `cd worker && pytest tests/test_cf_pipeline.py -x` | ❌ Wave 0 |
| REC-04 | Hybrid score uses alpha=1.0 below threshold; alpha=0.5 at/above; norm() handles max==min | unit | `cd backend && pytest tests/test_recommendations.py::test_hybrid_blending -x` | ❌ Wave 0 (add to existing file) |
| UI-05 | Like/dislike buttons render; clicking sends POST /api/feedback; optimistic state updates | manual (browser) | N/A — React component behavior | manual-only |
| API-03 | POST /api/feedback returns 204; upsert replaces action; 401 without JWT | integration | `cd backend && pytest tests/test_feedback.py -x` | ❌ Wave 0 |
| API-07 | 10 concurrent POST /api/recommendations return 200 within 3s | smoke | `cd backend && pytest tests/test_concurrency.py -x` | ❌ Wave 0 |
| SEC-03 | 11th request in 1 minute returns 429 with Retry-After header | integration | `cd backend && pytest tests/test_rate_limit.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/ -x -q` (backend only, or `cd worker && pytest tests/ -x -q` for worker tasks)
- **Per wave merge:** `cd backend && pytest tests/ && cd ../worker && pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_feedback.py` — covers DATA-03, API-03
- [ ] `backend/tests/test_rate_limit.py` — covers SEC-03
- [ ] `backend/tests/test_concurrency.py` — covers API-07
- [ ] `worker/tests/test_cf_pipeline.py` — covers REC-03
- [ ] Additional tests in `backend/tests/test_recommendations.py` — covers REC-04 hybrid blending
- [ ] `backend/app/core/limiter.py` — defines `Limiter` instance (needed before feedback router and main.py can import it)
- [ ] `shared/config.py` — add `INTERACTIONS_COLLECTION = "interactions"` constant
- [ ] `backend/requirements.txt` — add `slowapi==0.1.9`

*(All test files are new; existing test infrastructure (conftest.py, AsyncDatabase/AsyncCollection wrappers, seed_movies fixture) covers the foundation for DATA-03 and API-03 tests.)*

---

## Sources

### Primary (HIGH confidence)
- PyPI `slowapi` 0.1.9 — version, dependencies, Python support verified 2026-03-26
- `backend/app/main.py` — lifespan artifact loading pattern (direct read)
- `backend/app/services/recommendation_service.py` — scoring and candidate pipeline (direct read)
- `backend/app/repositories/user_preferences_repo.py` — upsert pattern (direct read)
- `worker/jobs/nlp_features.py` — batch job pattern, `build_similarity_index` row-by-row approach (direct read)
- `backend/tests/conftest.py` — AsyncCollection/AsyncDatabase wrappers, mongomock pattern (direct read)
- `frontend/src/hooks/useRecommendations.ts` — useMutation hook pattern (direct read)
- `frontend/src/pages/RecommendationsPage.tsx` — card structure, line 241 insertion point (direct read)
- `frontend/src/lib/types.ts` — existing type definitions to extend (direct read)
- `.planning/phases/03-collaborative-filtering-and-hybrid-engine/03-CONTEXT.md` — locked decisions (direct read)

### Secondary (MEDIUM confidence)
- [MovieLens 20M README](https://files.grouplens.org/datasets/movielens/ml-20m-README.html) — `links.csv` column format (`movieId,imdbId,tmdbId`), `ratings.csv` format, 5-star scale confirmed
- [slowapi GitHub](https://github.com/laurentS/slowapi) — `request: Request` requirement for decorated endpoints, SlowAPIMiddleware setup, 429 behavior
- [TanStack Query Optimistic Updates docs](https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates) — `useMutation` with `onMutate`/`onError` rollback pattern
- [scikit-learn cosine_similarity docs](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.html) — sparse matrix input support

### Tertiary (LOW confidence)
- tmdbId coverage percentage in MovieLens-20M corpus — not directly documented; ~60–80% match estimate is based on general dataset overlap knowledge, not verified against actual data

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements files except slowapi; slowapi version confirmed on PyPI
- Architecture: HIGH — patterns derived directly from reading existing codebase (nlp_features.py, recommendation_service.py, conftest.py, main.py)
- CF algorithm: HIGH — item-based CF with scipy sparse + sklearn cosine_similarity is standard; mirrors existing NLP similarity index pattern exactly
- slowapi integration: HIGH — verified against PyPI and GitHub; `request: Request` requirement is a known critical constraint
- MovieLens data mapping: MEDIUM — links.csv tmdbId column format confirmed; NaN handling is standard CSV caution; exact coverage % is LOW
- Pitfalls: HIGH — all pitfalls derive from direct code reading (conftest.py wrapper surface, lifespan fallback pattern, existing limiter gap)

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (slowapi is stable; scikit-learn/scipy are stable; MovieLens format is fixed)
