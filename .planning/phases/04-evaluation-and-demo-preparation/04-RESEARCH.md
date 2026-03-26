# Phase 4: Evaluation and Demo Preparation - Research

**Researched:** 2026-03-26
**Domain:** Recommendation system evaluation (Precision@K, NDCG@K), demo data management, cold-start robustness testing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Evaluation metrics**
- Precision@10 and NDCG@10 only — K=10 matches the system's Top-10 output; no need to report K=5
- Evaluation script — a standalone Python script (`worker/jobs/evaluate.py` or similar) that runs against a held-out subset of MovieLens-20M interactions and prints/stores results
- Split strategy: leave-one-out per user — hold out each qualifying test user's most recent liked movie as the ground truth; all their other likes are training signal
- Minimum 5 likes per test user — matches CF_THRESHOLD (5 likes = 4 training + 1 test); users below this threshold are excluded from the test set
- Test set size: 100–500 users — statistically meaningful for a capstone, fast to compute; randomly sample qualifying users up to 500

**Metrics storage and display**
- Eval script writes results to a `metrics.json` file in the artifacts directory
- JSON format: `{ "precision_at_10": X, "ndcg_at_10": Y, "eval_date": "YYYY-MM-DD", "n_users": N }`
- API loads `metrics.json` at startup (lifespan); exposes `GET /api/metrics` endpoint
- Frontend shows a small metrics card on the Recommendations page, below the page header
- Card is only shown when metrics are available (API returns data), hidden on 404

**Demo data and reset**
- Two demo accounts pre-seeded: `demo_returning` (5+ likes, CF-blended) and `demo_coldstart` (fresh)
- Fresh registration performed live during demo to show full onboarding flow
- Demo reset script (`worker/jobs/reset_demo.py`) — removes added interactions, re-seeds `demo_returning`, deletes UAT test accounts

**UAT sessions**
- Each student gets a fresh account (registers at session start)
- Run `reset_demo.py` between UAT participants
- Success criteria: at least 5 students complete a full session without crash or unhandled error

**Cold-start robustness**
- New user / no genre match fallback: if selected genres produce zero seed movies, fall back to globally top-rated movies
- Sparse system / missing CF artifact: system already falls back to alpha=1.0 (pure content); requires explicit test coverage
- Obscure movie with no CF neighbors: CF contribution defaults to 0.0; no code change needed, test coverage required

### Claude's Discretion
- Exact metrics card visual design (size, placement, color scheme)
- Eval script argument parsing (CLI flags for artifact path, test set size, output path)
- Whether metrics card shows a tooltip explaining what Precision@10/NDCG@10 mean
- Whether the reset script supports a `--dry-run` flag

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

</user_constraints>

---

## Summary

Phase 4 is entirely additive: all recommendation logic, feedback, and hybrid blending are complete from Phases 2–3. This phase adds four discrete deliverables: (1) an offline evaluation script that measures Precision@10 and NDCG@10 using leave-one-out splitting on MovieLens-20M data, (2) a `/api/metrics` endpoint and frontend metrics card to surface results, (3) a demo reset script that makes pre-presentation state restoration repeatable, and (4) targeted test coverage for all three cold-start scenarios.

The evaluation methodology is straightforward: filter qualifying users (5+ likes), sort their interactions by timestamp, hold out the most recent like as ground truth, feed the remaining likes as the user's training signal to `get_recommendations()`, and check whether the held-out movie appears in the returned Top-10. Precision@10 is the fraction of users where it does; NDCG@10 accounts for rank position. The recommendation service is already implemented and ready to be called directly from the eval script — no HTTP involved.

The single most important implementation risk is the genre-fallback for cold-start: if a user selects a genre that has no seed movies in the DB (which should be extremely rare but is theoretically possible), the current `recommendation_service.py` returns an empty list rather than falling back. This is the only code change required in Phase 4. Everything else is new scripts and test coverage.

**Primary recommendation:** Implement deliverables in dependency order — evaluate.py first (standalone, verifiable), then the genre fallback + cold-start tests, then metrics API endpoint, then frontend card, then reset_demo.py.

---

## Standard Stack

### Core (already in requirements.txt — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.6.0,<2.0.0 | `ndcg_score()` for NDCG@K computation | Already used for NLP/CF; `ndcg_score` is in `sklearn.metrics` |
| numpy | >=2.0.0 | Array manipulation for eval score accumulation | Already used throughout worker |
| joblib | >=1.3.0 | Load similarity_index.joblib and cf_index.joblib | Already used in all worker jobs |
| pymongo (AsyncMongoClient) | >=4.10.0 | Read interactions from MongoDB in evaluate.py | Already the project's MongoDB driver |
| python-dotenv | >=1.0.0 | `.env` loading in evaluate.py and reset_demo.py | Already used in all worker scripts |

### Supporting (frontend — no new packages)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | already installed | `useMetrics` hook follows `useRecommendations` pattern | Fetching GET /api/metrics with graceful 404 handling |
| React | already installed | Metrics card component in RecommendationsPage.tsx | Conditional render when data present |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sklearn.metrics.ndcg_score` | Manual NDCG formula | No reason to hand-roll — sklearn's implementation is correct and already a dependency |
| Direct service call in evaluate.py | HTTP call to running API | Direct call avoids network dependency during evaluation; eval runs offline against DB |

**Installation:** No new packages required. All libraries are already in `worker/requirements.txt` and `backend/requirements.txt`.

---

## Architecture Patterns

### Recommended File Structure (new files only)

```
worker/
└── jobs/
    ├── evaluate.py          # NEW: offline eval script (follows cf_features.py pattern)
    └── reset_demo.py        # NEW: demo reset script (follows seed_interactions.py pattern)

backend/
└── app/
    ├── api/routes/
    │   └── metrics.py       # NEW: GET /api/metrics route
    └── main.py              # MODIFIED: load metrics.json in lifespan

frontend/
└── src/
    ├── hooks/
    │   └── useMetrics.ts    # NEW: hook following useRecommendations pattern
    └── pages/
        └── RecommendationsPage.tsx  # MODIFIED: metrics card inserted below <h1>
```

### Pattern 1: Offline Evaluation Script (evaluate.py)

**What:** Standalone asyncio script that reads interactions from MongoDB, builds a leave-one-out test set, calls `RecommendationService.get_recommendations()` directly (not via HTTP), computes Precision@10 and NDCG@10, and writes `metrics.json`.

**When to use:** Run once after Phase 4 implementation, before the capstone presentation. May be rerun on updated interaction data.

**Structure follows cf_features.py exactly:**
```python
# Source: worker/jobs/cf_features.py (established pattern)
async def main() -> None:
    load_dotenv(...)
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]
    # ... compute metrics ...
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Key evaluation logic:**
```python
# Leave-one-out split: sort by timestamp, hold out last "like" per user
from collections import defaultdict

def build_test_set(interactions: list[dict], min_likes: int = 5, max_users: int = 500):
    """Return list of (user_id, held_out_movie_id, training_likes) tuples."""
    user_likes = defaultdict(list)
    for ia in interactions:
        if ia["action"] == "like":
            user_likes[ia["user_id"]].append(ia)

    test_users = []
    for user_id, likes in user_likes.items():
        if len(likes) < min_likes:
            continue
        # Sort by timestamp ascending; hold out the last one
        sorted_likes = sorted(likes, key=lambda x: x.get("timestamp", 0))
        held_out = sorted_likes[-1]["movie_id"]
        training = [ia["movie_id"] for ia in sorted_likes[:-1]]
        test_users.append((user_id, held_out, training))

    # Random sample up to max_users
    import random
    random.shuffle(test_users)
    return test_users[:max_users]
```

**NDCG@10 computation using sklearn:**
```python
# Source: sklearn.metrics documentation — ndcg_score expects 2D arrays
from sklearn.metrics import ndcg_score
import numpy as np

def compute_ndcg_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Return NDCG@K for a single user. 1.0 if relevant_id at position 0, decreasing by rank."""
    # y_true: relevance scores (1 for ground truth, 0 otherwise)
    # y_score: ranking scores (use inverse rank position)
    y_true = np.zeros((1, k))
    y_score = np.zeros((1, k))
    for rank, mid in enumerate(recommended_ids[:k]):
        y_score[0, rank] = k - rank  # higher score = higher rank
        if mid == relevant_id:
            y_true[0, rank] = 1.0
    if y_true.sum() == 0:
        return 0.0
    return float(ndcg_score(y_true, y_score))
```

**Important:** `recommendation_service.py` needs a `MockState` object and a `MockDB` to work offline. The eval script must replicate the app state setup (load NLP + CF artifacts from disk, wrap DB access). Alternatively, accept `app_state` as an object with the same attributes as `app.state`. Direct construction is simpler:

```python
class EvalState:
    """Mimics app.state for offline evaluation."""
    def __init__(self, nlp_data, cf_data):
        self.tfidf_vectorizer = None
        self.tmdb_ids = nlp_data["tmdb_ids"]
        self.top_indices = nlp_data["top_indices"]
        self.cf_top_indices = cf_data.get("cf_top_indices") if cf_data else None
        self.cf_tmdb_ids = cf_data["tmdb_ids"] if cf_data else []
```

### Pattern 2: GET /api/metrics Endpoint

**What:** New FastAPI route in `backend/app/api/routes/metrics.py`, loaded in `main.py`. Returns `app.state.metrics` (set at lifespan startup from `metrics.json`) or 404 if file was absent.

**Structure follows recommendations.py exactly:**
```python
# Source: backend/app/api/routes/recommendations.py (established router pattern)
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("")
async def get_metrics(request: Request):
    metrics = getattr(request.app.state, "metrics", None)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not yet computed")
    return metrics
```

**main.py lifespan addition:**
```python
# After CF artifact loading block — follows same pattern
metrics_path = os.path.join(artifacts_dir, "metrics.json")
if os.path.exists(metrics_path):
    import json
    with open(metrics_path) as f:
        app.state.metrics = json.load(f)
    logger.info("Metrics artifact loaded at startup")
else:
    app.state.metrics = None
    logger.info("metrics.json not found — /api/metrics will return 404")
```

### Pattern 3: useMetrics Hook (Frontend)

**What:** React Query hook following `useRecommendations` pattern. Returns `null` on 404 (metrics not computed) rather than throwing.

```typescript
// Source: frontend/src/hooks/useRecommendations.ts (established hook pattern)
export function useMetrics() {
  return useQuery<MetricsData | null>({
    queryKey: ['metrics'],
    queryFn: async () => {
      try {
        const { data } = await api.get<MetricsData>('/metrics');
        return data;
      } catch (err: any) {
        if (err?.response?.status === 404) return null;
        throw err;
      }
    },
    staleTime: 60 * 60 * 1000,  // 1 hour — metrics don't change during a session
    retry: false,
  });
}
```

**New type in types.ts:**
```typescript
export interface MetricsData {
  precision_at_10: number;
  ndcg_at_10: number;
  eval_date: string;
  n_users: number;
}
```

### Pattern 4: Metrics Card in RecommendationsPage.tsx

**Placement:** Inserted after the `<h1>` and before the EditPreferencesControl `<div>` in the results view (the `return` block starting at line 198 of the current file). Does NOT appear in the "no preferences submitted" state.

**Conditional rendering:**
```tsx
{/* Metrics card — only shown when metrics are available */}
{metrics && (
  <div className="mb-4 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-4 py-2">
    Precision@10: {metrics.precision_at_10.toFixed(3)} | NDCG@10:{' '}
    {metrics.ndcg_at_10.toFixed(3)} | Evaluated on {metrics.n_users} users
  </div>
)}
```

### Pattern 5: reset_demo.py Script

**What:** Idempotent CLI script that resets demo state before presentations and between UAT sessions.

**Structure follows seed_interactions.py:**
```python
async def main() -> None:
    load_dotenv(...)
    # Step 1: Delete all interactions for demo_returning added since last reset
    # (keep only the canonical seeded interactions from MovieLens)
    # Step 2: Re-seed demo_returning with canonical 5+ likes
    # Step 3: Delete UAT test accounts (by email prefix or by creation date)
    # Step 4: Print confirmation summary
```

**Demo account seeding strategy:** `demo_returning` account is a real MongoDB user (registered via auth endpoint during system setup, not a MovieLens seed_user_*). Its interactions are explicitly inserted with its `user_id` (MongoDB ObjectId string). The reset script deletes all interactions for `demo_returning.user_id` and re-inserts the canonical set. `demo_coldstart` has zero interactions — reset just confirms none exist.

### Anti-Patterns to Avoid

- **Calling GET /api/recommendations in evaluate.py:** Avoid HTTP calls in the eval script. Call `RecommendationService` directly to avoid network dependency, rate limiting, and auth overhead. The service is pure Python — instantiate with a mock state object.
- **Using seed_user_* accounts as eval test users:** The leave-one-out split should operate on real app users OR on a dedicated eval subset. Do NOT confuse MovieLens seed interactions (which drive CF training) with the eval test set. The test set should use interactions stored with real user_id values OR a separate filtered query.
- **Evaluating before CF artifacts are generated:** `evaluate.py` must load `cf_index.joblib` from the artifacts directory. Document clearly that the full pipeline (ingest → nlp_features → seed_interactions → cf_features → evaluate) must have run before evaluation results are meaningful.
- **Empty metrics card state causing layout shift:** The card must use a conditional block (`{metrics && ...}`) not a hidden element. A hidden element with `display:none` still occupies vertical space and would shift the page layout.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NDCG@K calculation | Custom DCG/IDCG formula | `sklearn.metrics.ndcg_score` | Already a dependency; handles edge cases (empty relevance, single item) correctly |
| JSON artifact I/O | Custom serialization | Python stdlib `json.load`/`json.dump` | metrics.json is a simple flat dict; no need for joblib here |
| Timestamp-based sort | Custom sort logic | `sorted(likes, key=lambda x: x.get("timestamp", 0))` | Single line; MongoDB interactions already store `updated_at` |
| React Query cache management | Custom fetch/cache | `useQuery` with `staleTime: 60min` | Already the project's data-fetching pattern |

**Key insight:** This phase is primarily about wiring existing components together. The recommendation service is already correct. The evaluation question is only "does the held-out movie appear in the top-10?" — no new algorithms needed.

---

## Common Pitfalls

### Pitfall 1: RecommendationService Requires genre_docs to Be Non-Empty

**What goes wrong:** `get_recommendations()` currently returns an empty list when no DB movies match the selected genres (`genre_docs` is empty after the `find()` call). During evaluation this is unlikely (test users have real liked movies with genres). But the CONTEXT.md spec requires explicit fallback to globally top-rated movies for this case — this IS a code change.

**Why it happens:** The current service assumes at least one genre-matching seed movie exists. The cold-start fallback for this scenario is not yet implemented.

**How to avoid:** Add a fallback block in `recommendation_service.py` immediately after the `genre_docs` query:
```python
if not genre_docs:
    # Fallback: use globally top-rated movies as seeds
    fallback_cursor = self._db.movies.find(
        {"rating": {"$ne": None}},
        {"tmdb_id": 1, "genres": 1},
        sort=[("rating", -1)],
        limit=TOP_K * 3,
    )
    genre_docs = await fallback_cursor.to_list(length=None)
```

**Warning signs:** Unit tests for "genre with zero DB movies" currently don't exist. Add them in Phase 4 before implementing the fallback.

### Pitfall 2: Evaluation on seed_user_* Interactions Inflates Scores

**What goes wrong:** MovieLens seed interactions (user_id like `"seed_user_12345"`) cover many more movies and users than real app interactions. If the eval script accidentally includes them, scores will be inflated (seed users have dense, clean interactions that perfectly match the CF index).

**Why it happens:** The interactions collection contains both real user interactions and seed_user_* interactions from `seed_interactions.py`.

**How to avoid:** Filter the eval query to exclude seed users:
```python
cursor = db.interactions.find({"user_id": {"$not": {"$regex": "^seed_user_"}}})
```
Or, alternatively, run evaluation against seed_user_* interactions intentionally (treating them as proxy "real users") — but document this choice explicitly. Either approach is valid; inconsistency is the risk.

### Pitfall 3: RecommendationService Uses async DB Calls — Eval Script Must Use Async Context

**What goes wrong:** `recommendation_service.py` uses `await cursor.to_list()`, `await interactions_repo.get_by_user_id()`, etc. If the eval script calls the service without an async context, it will fail.

**Why it happens:** The service was designed for FastAPI's async context. Scripts must use `asyncio.run()` with a proper async `main()` — which is already the pattern in `cf_features.py` and `seed_interactions.py`.

**How to avoid:** Follow the `cf_features.py` pattern: `async def main()` + `asyncio.run(main())`. The entire eval loop must be inside `async def main()`.

### Pitfall 4: metrics.json Must Exist Before Demo — Not Auto-Generated

**What goes wrong:** On the day of the capstone presentation, if `evaluate.py` was never run, `/api/metrics` returns 404 and the metrics card is hidden. This is correct behavior, but the presenter must remember to run `evaluate.py` beforehand and restart the API so the lifespan loads the new `metrics.json`.

**Why it happens:** `metrics.json` is loaded once at startup via the lifespan function, not read on every request.

**How to avoid:** Document in a `scripts/DEMO_CHECKLIST.md` (or inline in the eval script's docstring) that: (1) run `evaluate.py`, (2) restart `docker-compose up -d` so the API lifespan re-loads `metrics.json`.

### Pitfall 5: demo_returning User_ID Must Be a Real MongoDB ObjectId

**What goes wrong:** If `demo_returning` is set up as a seed_user_* style account (using a plain string ID), the CF blending logic that calls `interactions_repo.count_by_user_id(user_id)` will find no matches because the user's JWT `sub` claim won't match `"seed_user_123"`.

**Why it happens:** The auth system stores real user ObjectId strings in JWT `sub`. Seeded interactions for `demo_returning` must use that same ObjectId as the `user_id` field, not a synthetic string.

**How to avoid:** `reset_demo.py` must look up `demo_returning` by email from the users collection, retrieve its `_id`, and use that as `user_id` when inserting interactions. Document this in the reset script.

---

## Code Examples

### Precision@10 Computation

```python
# Direct binary precision — ground truth movie is either in Top-10 or not
def precision_at_k(recommended_ids: list[int], relevant_id: int, k: int = 10) -> float:
    """Return 1.0 if relevant_id is in top-k recommendations, 0.0 otherwise."""
    return 1.0 if relevant_id in recommended_ids[:k] else 0.0
```

### Leave-One-Out Split

```python
from collections import defaultdict
import random

def build_leave_one_out_test_set(
    interactions: list[dict],
    min_likes: int = 5,
    max_users: int = 500,
) -> list[tuple[str, int, list[int]]]:
    """Build (user_id, held_out_tmdb_id, training_tmdb_ids) tuples.

    Uses timestamp ordering. Each qualifying user contributes one test case.
    Returns random sample of up to max_users qualifying users.
    """
    user_likes: dict[str, list[dict]] = defaultdict(list)
    for ia in interactions:
        if ia.get("action") == "like":
            user_likes[ia["user_id"]].append(ia)

    test_set = []
    for user_id, likes in user_likes.items():
        if len(likes) < min_likes:
            continue
        sorted_likes = sorted(likes, key=lambda x: x.get("updated_at", 0))
        held_out = sorted_likes[-1]["movie_id"]
        training = [ia["movie_id"] for ia in sorted_likes[:-1]]
        test_set.append((user_id, held_out, training))

    random.shuffle(test_set)
    return test_set[:max_users]
```

### Evaluation Loop (Pseudocode)

```python
precision_scores = []
ndcg_scores = []

for user_id, held_out_id, training_ids in test_set:
    # Build a minimal user state for this evaluation
    # The service looks up genres from user preferences — use a fixed generic genre
    # OR pre-fetch the user's saved preferences from user_preferences collection
    user_prefs = await prefs_repo.get_by_user_id(user_id)
    if not user_prefs or not user_prefs.get("genres"):
        continue  # skip users with no saved preferences

    result = await service.get_recommendations(
        genres=user_prefs["genres"],
        mood=user_prefs.get("mood"),
        user_id=user_id,
    )
    recommended_ids = [r.tmdb_id for r in result.recommendations]

    precision_scores.append(precision_at_k(recommended_ids, held_out_id))
    ndcg_scores.append(compute_ndcg_at_k(recommended_ids, held_out_id))

metrics = {
    "precision_at_10": sum(precision_scores) / len(precision_scores),
    "ndcg_at_10": sum(ndcg_scores) / len(ndcg_scores),
    "eval_date": date.today().isoformat(),
    "n_users": len(precision_scores),
}
```

### Genre Fallback in recommendation_service.py

```python
# Source: recommendation_service.py get_recommendations() — add after genre_docs fetch
genre_docs = await cursor.to_list(length=None)

# Cold-start fallback: if no genre-matching movies found, use top-rated
if not genre_docs:
    logger.warning("No movies match selected genres %s — falling back to top-rated", genres)
    fallback_cursor = self._db.movies.find(
        {"rating": {"$ne": None}},
        {"tmdb_id": 1, "genres": 1},
        sort=[("rating", -1)],
        limit=TOP_K * 3,
    )
    genre_docs = await fallback_cursor.to_list(length=None)
```

**Note:** The `sort` parameter is passed to `.find()` as a keyword argument. In PyMongo v4+ async driver this is valid. Alternatively chain `.sort("rating", -1)`.

### reset_demo.py Core Logic

```python
async def reset_demo(db, demo_returning_email: str, uat_prefix: str, canonical_likes: list[int]):
    # 1. Find demo_returning user_id
    user = await db.users.find_one({"email": demo_returning_email})
    if not user:
        logger.error("demo_returning user not found in DB — run setup first")
        return
    user_id = str(user["_id"])

    # 2. Delete all interactions for demo_returning
    result = await db.interactions.delete_many({"user_id": user_id})
    logger.info(f"Deleted {result.deleted_count} interactions for demo_returning")

    # 3. Re-seed canonical likes
    for tmdb_id in canonical_likes:
        await db.interactions.update_one(
            {"user_id": user_id, "movie_id": tmdb_id},
            {"$set": {"user_id": user_id, "movie_id": tmdb_id, "action": "like",
                       "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    logger.info(f"Re-seeded {len(canonical_likes)} canonical likes for demo_returning")

    # 4. Delete UAT accounts (registered with test email prefix)
    uat_users = await db.users.find(
        {"email": {"$regex": f"^{uat_prefix}"}}
    ).to_list(length=None)
    uat_ids = [str(u["_id"]) for u in uat_users]
    await db.interactions.delete_many({"user_id": {"$in": uat_ids}})
    await db.users.delete_many({"email": {"$regex": f"^{uat_prefix}"}})
    logger.info(f"Deleted {len(uat_users)} UAT accounts and their interactions")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate Motor library for async MongoDB | PyMongo AsyncMongoClient directly | Motor deprecated May 2025 | Already decided in Phase 1 — eval/reset scripts use same pattern |
| `@tailwind directives` in CSS | `@import "tailwindcss"` with @tailwindcss/vite | Tailwind v4 | Already in project — metrics card uses existing Tailwind classes |

**No deprecated patterns relevant to this phase.**

---

## Open Questions

1. **Eval test user source: real users or seed_user_* accounts?**
   - What we know: Both real users and seed_user_* interactions are in the interactions collection. Seed users have clean, dense MovieLens data. Real users (during UAT) will be sparse at the time evaluate.py runs.
   - What's unclear: If evaluate.py runs BEFORE UAT sessions, there may be very few real users with 5+ likes. The spec says "held-out subset of MovieLens-20M interactions" — implying seed_user_* accounts ARE the intended eval population.
   - Recommendation: Use seed_user_* interactions as the eval population (they represent dense, realistic taste profiles). Document this explicitly in the script. Add a CLI flag `--use-seed-users` defaulting to `True`.

2. **User preferences required by RecommendationService.get_recommendations()**
   - What we know: `get_recommendations()` takes `genres` and `mood` as arguments. Seed users don't have entries in `user_preferences` collection (only real app users do).
   - What's unclear: How should the eval script determine which genres to pass for a seed_user_* test case?
   - Recommendation: Derive genres from the training likes — collect all genres from movies the user liked, pick the top 2 most frequent. This ensures the eval call is realistic without requiring saved preferences. Alternatively, use a fixed "Action, Drama" for all eval users (simpler, slightly less realistic).

3. **demo_returning account creation: manual or scripted?**
   - What we know: `demo_returning` must be a real MongoDB user (not a seed_user_*) so its JWT works for CF blending.
   - What's unclear: Should there be a separate `setup_demo_accounts.py` one-time script, or should `reset_demo.py` create accounts if they don't exist?
   - Recommendation: `reset_demo.py` handles both creation (first run) and reset (subsequent runs). Check if user exists; if not, register via the auth route or direct DB insert. Document that this script must be run once before the first UAT session.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already configured) |
| Config file (backend) | `backend/pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Config file (worker) | `worker/pytest.ini` — `asyncio_mode = auto`, `testpaths = tests` |
| Quick run command (backend) | `cd backend && python -m pytest tests/test_recommendations.py tests/test_metrics.py -x` |
| Quick run command (worker) | `cd worker && python -m pytest tests/test_eval_pipeline.py -x` |
| Full suite command | `cd backend && python -m pytest && cd ../worker && python -m pytest` |

### Phase Requirements to Test Map

| Deliverable | Behavior | Test Type | Automated Command | File Exists? |
|-------------|----------|-----------|-------------------|-------------|
| Genre fallback (cold-start) | genre with zero DB matches returns TOP_K results, not empty list | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_genre_fallback_returns_results -x` | ❌ Wave 0 |
| Missing CF artifact cold-start | cf_top_indices=None + user with 5 interactions returns valid results | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_no_cf_artifact_falls_back -x` | ✅ exists |
| Obscure movie no CF neighbors | movie with zero CF scores still gets scored via content path | unit | `cd backend && python -m pytest tests/test_recommendations.py::test_obscure_movie_no_cf_neighbors -x` | ❌ Wave 0 |
| GET /api/metrics — metrics loaded | returns 200 with precision/ndcg values when metrics.json was loaded | unit | `cd backend && python -m pytest tests/test_metrics.py::test_metrics_returns_200 -x` | ❌ Wave 0 |
| GET /api/metrics — no metrics.json | returns 404 when metrics not loaded | unit | `cd backend && python -m pytest tests/test_metrics.py::test_metrics_returns_404 -x` | ❌ Wave 0 |
| build_leave_one_out_test_set | users with <5 likes excluded; returns correct (user, held_out, training) structure | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_leave_one_out_split -x` | ❌ Wave 0 |
| Precision@10 computation | returns 1.0 when relevant_id in top-10, 0.0 otherwise | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_precision_at_k -x` | ❌ Wave 0 |
| NDCG@10 computation | returns higher score for relevant item at rank 1 vs rank 5 | unit | `cd worker && python -m pytest tests/test_eval_pipeline.py::test_ndcg_at_k -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/test_recommendations.py -x -q && cd ../worker && python -m pytest tests/test_eval_pipeline.py -x -q`
- **Per wave merge:** Full suite — `cd backend && python -m pytest -q && cd ../worker && python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_metrics.py` — covers GET /api/metrics 200 and 404 cases
- [ ] `backend/tests/test_recommendations.py::test_genre_fallback_returns_results` — new test in existing file
- [ ] `backend/tests/test_recommendations.py::test_obscure_movie_no_cf_neighbors` — new test in existing file
- [ ] `worker/tests/test_eval_pipeline.py` — covers leave-one-out split, precision@k, ndcg@k

---

## Sources

### Primary (HIGH confidence)

- Codebase direct read — `backend/app/main.py` lifespan pattern for artifact loading
- Codebase direct read — `worker/jobs/cf_features.py` batch script pattern
- Codebase direct read — `worker/jobs/seed_interactions.py` DB seeding pattern
- Codebase direct read — `backend/app/services/recommendation_service.py` service interface
- Codebase direct read — `frontend/src/hooks/useRecommendations.ts` hook pattern
- Codebase direct read — `backend/tests/conftest.py` test fixture patterns
- `worker/requirements.txt` and `backend/requirements.txt` — verified package versions

### Secondary (MEDIUM confidence)

- scikit-learn `ndcg_score` — in `sklearn.metrics` since v0.24; stable API, no version concerns given >=1.6.0 constraint
- Standard IR metrics (Precision@K, NDCG@K) — well-established academic formulas, no library API ambiguity

### Tertiary (LOW confidence)

- None — all research findings are grounded in direct codebase inspection or stable library APIs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via requirements.txt; no new dependencies needed
- Architecture: HIGH — all patterns copied directly from existing codebase files
- Pitfalls: HIGH — identified from direct code inspection of recommendation_service.py, interactions_repo.py, and seed_interactions.py
- Evaluation methodology: HIGH — leave-one-out is standard IR practice; sklearn ndcg_score is well-documented

**Research date:** 2026-03-26
**Valid until:** 2026-06-26 (stable codebase; no fast-moving external dependencies in scope)
