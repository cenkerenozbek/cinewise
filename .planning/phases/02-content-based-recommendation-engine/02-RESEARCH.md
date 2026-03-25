# Phase 2: Content-Based Recommendation Engine - Research

**Researched:** 2026-03-26
**Domain:** NLP (TF-IDF), content-based recommendation, FastAPI ML serving, React preference UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dedicated `/recommendations` route — not embedded in homepage
- Accessed via a "For You" navbar link, visible after login
- If no preferences are set yet, the `/recommendations` page shows the preference form inline (onboarding and results live on the same page — no separate `/onboarding` route)
- Results use the existing `MovieCard` grid layout (reuse `MovieCard` + `MovieGrid`)
- Top-K = 10 movies per recommendation session
- Genre selection: multi-select chip/toggle buttons (genres dynamically loaded from DB via existing `/movies/genres` endpoint)
- Mood selection: optional, single-select chips in the same visual style as genre chips; clearly labeled "optional"
- Minimum 1 genre required; mood is optional — validation enforced before fetching recommendations
- Preferences are editable on the `/recommendations` page via an "Edit preferences" button or collapsible section; user can update and re-fetch without leaving the page
- Explanation format: short sentence referencing the user's selected preferences — e.g., "Recommended because you like Action and Thriller"
- Explanation rendered in small text below each `MovieCard` (not a tooltip, not behind a click — always visible)
- Mood options (exactly these 5): Happy, Tense, Relaxing, Mind-bending, Romantic
- Mood influence: mood boosts movies whose genres match a predefined mapping (Tense → Thriller, Horror; Romantic → Romance, Drama; Happy → Comedy, Animation; Relaxing → Documentary, Drama; Mind-bending → Sci-Fi, Mystery)

### Claude's Discretion
- Exact TF-IDF hyperparameters (max_features, ngram_range, stop words)
- Similarity index storage format (pickle, HDF5, or joblib — whatever loads fastest at startup)
- NLP text field composition (overview only, or overview + genre names)
- Genre-to-mood boost weight values (e.g., 1.2x multiplier)
- Preferences persistence model (new MongoDB collection vs. field on user document)
- Error/loading states on the recommendations page

### Deferred Ideas (OUT OF SCOPE)
- Like/dislike feedback on recommendation cards — Phase 3
- Collaborative filtering signal — Phase 3
- Hybrid blending of content + collaborative scores — Phase 3
- Rate limiting on recommendation endpoint — Phase 3
- Watched list / recommendation history — v2
- Bilingual mood labels (TR/EN) — v2 out-of-scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NLP-01 | System preprocesses movie summary text (normalization, HTML cleaning, tokenization) | scikit-learn TfidfVectorizer handles lowercasing, tokenization, stop word removal natively; HTML cleaning needs `html.unescape` + strip |
| NLP-02 | System extracts TF-IDF vectors from movie summaries | `TfidfVectorizer.fit_transform()` on overview (+ optional genre names) corpus |
| NLP-03 | System builds precomputed similarity index (top-N similar movies per movie) | `cosine_similarity` on TF-IDF matrix → argsort → store top-50 per movie as numpy array |
| NLP-04 | System extracts keywords/themes from summaries to support recommendation explanations | User-selected genres serve as the explanation source (no keyword extraction needed; explanation is "because you like [genres]") |
| REC-01 | System generates Top-K personalized movie recommendations | Score = cosine similarity sum over genre-matched movies + optional mood boost; rank, return top 10 |
| REC-02 | System implements content-based recommendation using cosine similarity on TF-IDF | Precomputed top-50 similarity index loaded at FastAPI startup from disk |
| REC-05 | System handles cold-start users by relying on content-based + explicit preferences | Genre + mood preferences captured at first visit; no interaction history required |
| UI-02 | User can specify genre preferences and optional mood selection (cold-start onboarding) | Multi-select genre chips via `useGenres()`, single-select mood chips; form lives on `/recommendations` page |
| UI-04 | User can view recommendation results with poster, title, year, summary, and explanation | Reuse `MovieCard` + `MovieGrid`; add `explanation` field below card |
| API-02 | System exposes REST endpoint for recommendation retrieval | `POST /api/recommendations` — accepts genres + mood, returns top-10 with explanation |
| API-05 | Recommendation API responds within 3 seconds (p95) | Precomputed artifacts loaded at startup; per-request work is O(K) lookup + sort |
</phase_requirements>

---

## Summary

Phase 2 builds a content-based recommendation engine on top of the Phase 1 data foundation. The architecture is a two-component system: (1) an offline NLP batch pipeline in the worker that preprocesses movie summaries, builds TF-IDF vectors, and writes a precomputed top-50 cosine-similarity index to disk; and (2) a FastAPI recommendation endpoint that loads those precomputed artifacts at startup and serves per-request lookups in memory without recomputing NLP.

The NLP pipeline uses scikit-learn's `TfidfVectorizer` (HIGH confidence — well-established library, confirmed v1.6.1 installed). Precomputed artifacts are stored with `joblib.dump` (HIGH confidence — standard sklearn persistence, fastest for large numpy arrays). The FastAPI lifespan pattern already used in `main.py` for MongoDB is extended to load artifacts into `app.state`. The React frontend adds a `/recommendations` route with preference chips (genre + mood), reuses `MovieCard`/`MovieGrid`, and persists preferences to a new `user_preferences` MongoDB collection.

**Primary recommendation:** Use `TfidfVectorizer(max_features=5000, ngram_range=(1,2), stop_words='english', sublinear_tf=True)` on `overview + ' ' + ' '.join(genres)` composite text. Store artifacts as two joblib files: `tfidf_vectorizer.joblib` and `similarity_index.npy`. Load both into `app.state` at FastAPI startup. Score per request by summing similarity rows for user-preferred genre-matched movies, apply mood boost multiplier (1.3x), rank, return top 10.

---

## Standard Stack

### Core (NLP Pipeline — Worker)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.6.0 | TfidfVectorizer, cosine_similarity | Industry-standard; already available (v1.6.1 confirmed installed locally); TfidfVectorizer handles all text preprocessing |
| numpy | >=2.0.0 | Array operations, argsort for top-N, storing index | Dependency of scikit-learn; needed for numerical index storage |
| scipy | >=1.17.0 | Sparse matrix output of TfidfVectorizer | Dependency of scikit-learn; TF-IDF matrix is sparse |
| joblib | >=1.3.0 | Serialize/deserialize vectorizer and similarity index | Faster than pickle for numpy arrays; standard sklearn persistence tool |

### Core (Backend — Serving)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.6.0 | Load pickled TfidfVectorizer (deserialization only) | Same version as worker to ensure pickle compatibility |
| numpy | >=2.0.0 | Load precomputed similarity index, array operations | Required for in-memory index operations |
| joblib | >=1.3.0 | `joblib.load()` artifacts at startup | Same reason as worker |

### Core (Frontend — React)

All frontend libraries already installed. No new packages needed.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | ^5.95.2 (already installed) | `useRecommendations` hook — server-state caching | Already used for all data fetching in project |
| axios | ^1.13.6 (already installed) | HTTP calls via existing `api.ts` instance | Already used |
| tailwindcss v4 | ^4.2.2 (already installed) | Chip/toggle styling for preference form | Already used throughout |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| html.unescape (stdlib) | Python stdlib | Unescape HTML entities in TMDB overview text | In NLP preprocessing step before TF-IDF |
| re (stdlib) | Python stdlib | Strip extra whitespace/special chars from text | In NLP preprocessing step |
| pytest | >=8.0.0 (already installed) | Test NLP pipeline and recommendation service | Already used for all tests |
| mongomock | >=4.2.0 (already installed) | Mock MongoDB for user_preferences repo tests | Already used for movie/auth tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| joblib for artifacts | pickle | pickle is slower for large numpy arrays; joblib is the sklearn-recommended approach |
| joblib for artifacts | scipy.sparse.save_npz + numpy.save | Two files + two load calls; joblib.dump can bundle vectorizer + array in one file; joblib is simpler |
| composite text (overview + genres) | overview only | Overview-only misses genre signal; genre names in text boosted by IDF give lightweight genre-awareness for free |
| numpy .npy for top-N index | HDF5 via h5py | h5py adds a heavy dependency; numpy .npy via `np.save`/`np.load` with memmap support is simpler; joblib wraps this natively |
| mongomock AsyncCollection wrapper | real pytest-mongodb | Existing AsyncDatabase/AsyncCollection wrapper in conftest already proven; adding new collection follows same pattern |

**Installation (worker/backend additions):**
```bash
pip install scikit-learn>=1.6.0 numpy>=2.0.0 scipy>=1.17.0 joblib>=1.3.0
```

**Version verification (confirmed via PyPI March 2026):**
- scikit-learn: 1.8.0 (stable, December 2025) — use `>=1.6.0` in requirements to match what's installed
- numpy: 2.4.3 (latest, March 2026)
- scipy: 1.17.1 (latest, February 2026)
- joblib: bundled with scikit-learn, also `joblib>=1.3.0` standalone

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
worker/
├── jobs/
│   └── nlp_features.py          # NEW: NLP batch job (fetch→preprocess→vectorize→save)
├── pipelines/
│   └── nlp/
│       ├── fetch_texts.py       # NEW: Load movie overviews + genres from MongoDB
│       ├── transform_texts.py   # NEW: Text normalization, composite text assembly
│       └── build_index.py       # NEW: TF-IDF fit_transform + cosine similarity + save artifacts
├── tests/
│   └── test_nlp_pipeline.py     # NEW: Unit tests for NLP stages

backend/
├── app/
│   ├── api/routes/
│   │   └── recommendations.py   # NEW: POST /api/recommendations router
│   ├── models/
│   │   └── recommendation.py    # NEW: Pydantic models (PreferenceRequest, RecommendationItem, etc.)
│   ├── repositories/
│   │   └── user_preferences_repo.py  # NEW: MongoDB CRUD for user_preferences collection
│   ├── services/
│   │   └── recommendation_service.py # NEW: Scoring logic using app.state artifacts
│   └── main.py                  # MODIFY: load NLP artifacts in lifespan, mount new router
├── tests/
│   └── test_recommendations.py  # NEW: Tests for recommendation endpoint

frontend/src/
├── pages/
│   └── RecommendationsPage.tsx  # NEW: Preference form + results page
├── hooks/
│   └── useRecommendations.ts    # NEW: React Query hook for POST /api/recommendations
├── components/
│   └── PreferenceChips.tsx      # NEW: Genre + mood chip selector component
├── lib/
│   └── types.ts                 # MODIFY: Add RecommendationItem, UserPreferences types
├── App.tsx                      # MODIFY: Add /recommendations route
└── components/Navbar.tsx        # MODIFY: Add "For You" link (authenticated only)

artifacts/                       # SHARED VOLUME (new docker-compose volume)
├── tfidf_vectorizer.joblib
├── tfidf_matrix.joblib
└── similarity_index.npy
```

### Pattern 1: NLP Batch Pipeline (fetch → transform → build)

**What:** Worker job reads all movie documents from MongoDB, assembles composite text, runs TF-IDF fit_transform, computes cosine similarity, stores top-50 per movie as a (N, 50) numpy int index array.

**When to use:** Run once after initial TMDB ingestion; re-run if corpus changes significantly.

**Example:**
```python
# worker/jobs/nlp_features.py — follows ingest_tmdb.py class pattern
import asyncio
import logging
import os
import html
import re
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import AsyncMongoClient

logger = logging.getLogger(__name__)


def preprocess_text(overview: str | None, genres: list[str]) -> str:
    """Normalize overview and append genre names for composite text."""
    text = overview or ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)          # strip any HTML tags
    text = re.sub(r"\s+", " ", text).strip()
    genre_str = " ".join(genres)
    return f"{text} {genre_str}".strip()


async def main():
    client = AsyncMongoClient(os.environ["MONGO_URI"])
    db = client[os.environ.get("DB_NAME", "movie_mrs")]

    cursor = db.movies.find({}, {"tmdb_id": 1, "overview": 1, "genres": 1})
    docs = await cursor.to_list(length=None)

    tmdb_ids = [d["tmdb_id"] for d in docs]
    texts = [preprocess_text(d.get("overview"), d.get("genres", [])) for d in docs]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)   # scipy sparse (N, 5000)

    # Compute cosine similarity in batches to avoid OOM for large N
    # For N=5000: full 5000x5000 float32 matrix = 100MB — manageable
    sim_matrix = cosine_similarity(tfidf_matrix, dense_output=False)

    # Build top-50 index: shape (N, 50) of integer indices
    TOP_N = 50
    top_indices = np.zeros((len(docs), TOP_N), dtype=np.int32)
    for i in range(len(docs)):
        row = np.asarray(sim_matrix[i].todense()).flatten()
        row[i] = 0.0  # exclude self
        top_indices[i] = np.argpartition(row, -TOP_N)[-TOP_N:]

    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    joblib.dump(vectorizer, f"{artifacts_dir}/tfidf_vectorizer.joblib")
    joblib.dump({"tmdb_ids": tmdb_ids, "top_indices": top_indices},
                f"{artifacts_dir}/similarity_index.joblib")

    logger.info(f"NLP artifacts written to {artifacts_dir} for {len(docs)} movies")
    client.close()
```

### Pattern 2: FastAPI Lifespan — Load Artifacts at Startup

**What:** Extend existing `lifespan` context manager in `main.py` to load NLP artifacts into `app.state` before serving.

**When to use:** Artifacts must be loaded ONCE at startup; all requests share the same in-memory objects.

**Example:**
```python
# backend/app/main.py (lifespan modification)
import joblib, numpy as np, os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing: MongoDB
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]
    await app.state.db.movies.create_index([("title", "text")])
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])

    # New: NLP artifacts
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    vectorizer_path = f"{artifacts_dir}/tfidf_vectorizer.joblib"
    index_path = f"{artifacts_dir}/similarity_index.joblib"
    if os.path.exists(vectorizer_path) and os.path.exists(index_path):
        app.state.tfidf_vectorizer = joblib.load(vectorizer_path)
        sim_data = joblib.load(index_path)
        app.state.tmdb_ids = sim_data["tmdb_ids"]       # list[int]
        app.state.top_indices = sim_data["top_indices"]  # np.ndarray (N, 50)
        logger.info("NLP artifacts loaded at startup")
    else:
        app.state.tfidf_vectorizer = None
        app.state.tmdb_ids = []
        app.state.top_indices = None
        logger.warning("NLP artifacts not found — recommendations unavailable until worker runs")

    yield

    app.state.mongo_client.close()
```

### Pattern 3: Recommendation Scoring

**What:** Per-request scoring — no NLP recomputation. Uses preloaded index + genre/mood preference to rank top-10.

**Example:**
```python
# backend/app/services/recommendation_service.py
class RecommendationService:
    def __init__(self, db, app_state):
        self.db = db
        self.state = app_state

    async def get_recommendations(
        self, user_id: str, genres: list[str], mood: str | None
    ) -> list[dict]:
        if self.state.top_indices is None:
            raise HTTPException(503, "Recommendation index not ready")

        # Find candidate movies: union of top-50 neighbors for each genre-matching movie
        genre_set = set(genres)
        cursor = self.db.movies.find(
            {"genres": {"$in": genres}},
            {"tmdb_id": 1, "genres": 1}
        )
        genre_docs = await cursor.to_list(length=None)

        # Map tmdb_id -> index position in precomputed array
        id_to_idx = {tid: i for i, tid in enumerate(self.state.tmdb_ids)}

        candidate_scores: dict[int, float] = {}
        for doc in genre_docs:
            idx = id_to_idx.get(doc["tmdb_id"])
            if idx is None:
                continue
            for neighbor_idx in self.state.top_indices[idx]:
                neighbor_id = self.state.tmdb_ids[neighbor_idx]
                candidate_scores[neighbor_id] = candidate_scores.get(neighbor_id, 0) + 1.0

        # Mood boost: apply 1.3x multiplier for movies matching mood genres
        if mood:
            mood_genre_map = {
                "Tense": ["Thriller", "Horror"],
                "Romantic": ["Romance", "Drama"],
                "Happy": ["Comedy", "Animation"],
                "Relaxing": ["Documentary", "Drama"],
                "Mind-bending": ["Science Fiction", "Mystery"],
            }
            boost_genres = set(mood_genre_map.get(mood, []))
            # Fetch genres for candidates (batch)
            # ... (boost candidates whose genres intersect boost_genres)

        # Remove movies the user already selected as preferences
        for genre_doc in genre_docs:
            candidate_scores.pop(genre_doc["tmdb_id"], None)

        # Rank by score, take top 10
        top_ids = sorted(candidate_scores, key=lambda k: candidate_scores[k], reverse=True)[:10]

        # Fetch full movie documents for top_ids
        docs = await self.db.movies.find({"tmdb_id": {"$in": top_ids}}).to_list(length=10)

        explanation = "Recommended because you like " + " and ".join(genres)
        return [{"movie": doc, "explanation": explanation} for doc in docs]
```

### Pattern 4: User Preferences Persistence

**What:** Store user genre + mood preferences in MongoDB `user_preferences` collection. Field on user document (simpler) vs. separate collection (more extensible) — recommendation: new `user_preferences` collection following `user_repo.py` pattern.

**Recommendation:** New `user_preferences` collection with `{user_id: str, genres: list[str], mood: str | None, updated_at: datetime}`. Index on `user_id` (unique). Follows repo pattern in `user_repo.py`.

### Pattern 5: React Preference Form (existing patterns)

**What:** `RecommendationsPage.tsx` uses `useGenres()` already exported from `useMovies.ts` for dynamic genre chips. Mood chips are hardcoded (5 fixed values). `useRecommendations` hook uses `useQuery` with `enabled: hasPreferences` to only fetch when genres selected.

**Example:**
```typescript
// frontend/src/hooks/useRecommendations.ts
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { RecommendationResponse } from '../lib/types';

export function useRecommendations(genres: string[], mood: string | null) {
  return useQuery<RecommendationResponse>({
    queryKey: ['recommendations', genres, mood],
    queryFn: async () => {
      const { data } = await api.post<RecommendationResponse>('/recommendations', {
        genres,
        mood,
      });
      return data;
    },
    enabled: genres.length > 0,
  });
}
```

```typescript
// frontend/src/lib/types.ts additions
export interface RecommendationItem {
  movie: MovieSummary;       // reuse existing MovieSummary
  explanation: string;       // "Recommended because you like Action and Thriller"
}

export interface RecommendationResponse {
  recommendations: RecommendationItem[];
}

export interface UserPreferences {
  genres: string[];
  mood: string | null;
}
```

### Anti-Patterns to Avoid

- **Computing TF-IDF on each API request:** Recomputing `fit_transform` per request would take 2-5 seconds on 5000 movies — violates API-05. Always precompute.
- **Full 5000x5000 dense float64 matrix in memory:** ~200MB float64; store only top-50 int32 indices per movie (~1MB), compute dense only transiently during batch.
- **Using `cosine_similarity` with `dense_output=True` for full matrix:** Produces a 200MB dense float64 matrix in a single call. For 5000 movies this is borderline (200MB). Use `dense_output=False` to keep sparse, then convert rows one at a time.
- **Storing NLP artifacts inside the backend container filesystem:** Artifacts written by worker won't be visible to backend without a shared Docker volume. Must add a shared named volume.
- **Using Motor or expecting mongomock native async:** Motor was deprecated May 2025, EOL May 2026. The existing AsyncCollection wrapper in `conftest.py` handles mongomock → async compatibility; extend same pattern for `user_preferences_repo`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TF-IDF text vectorization | Custom term freq / IDF calculator | `sklearn.feature_extraction.text.TfidfVectorizer` | Handles edge cases: empty strings, stop words, l2 normalization, vocabulary limits, sparse output |
| Cosine similarity | Manual dot products | `sklearn.metrics.pairwise.cosine_similarity` | Handles sparse matrices efficiently; linear_kernel alias for l2-normalized TF-IDF |
| Model/array serialization | Custom binary format | `joblib.dump` / `joblib.load` | Handles numpy arrays and scipy sparse with memory mapping; tested sklearn-compatible format |
| Text HTML cleaning | Regex-only parser | `html.unescape()` (stdlib) + regex whitespace strip | Sufficient for TMDB text (no full HTML docs); avoid adding beautifulsoup4 for this alone |
| Async-safe MongoDB wrappers | New async mock library | Existing `AsyncCollection`/`AsyncDatabase` wrapper in `backend/tests/conftest.py` | Already proven; extend with `user_preferences` collection support |

**Key insight:** The TF-IDF + precomputed index pattern is a solved problem in scikit-learn. The only custom logic needed is the genre/mood preference-to-score mapping, which is application-specific business logic (not a general NLP problem).

---

## Common Pitfalls

### Pitfall 1: Artifact Volume Not Shared Between Worker and Backend

**What goes wrong:** Worker writes `tfidf_vectorizer.joblib` to `/artifacts` inside the worker container. Backend container cannot see it. Backend loads `None` artifacts at startup. All recommendation requests return 503.

**Why it happens:** Current `docker-compose.yml` does not have a shared named volume for NLP artifacts — only `mongo_data` is a named volume. Worker and backend mount separate named volumes.

**How to avoid:** Add a named volume `nlp_artifacts` to `docker-compose.yml` and mount it in BOTH `worker` and `backend` services:
```yaml
  backend:
    volumes:
      - ./backend:/app
      - ./shared:/app/shared
      - nlp_artifacts:/artifacts   # ADD THIS

  worker:
    volumes:
      - ./worker:/app
      - ./shared:/app/shared
      - nlp_artifacts:/artifacts   # ADD THIS

volumes:
  mongo_data:
  nlp_artifacts:                   # ADD THIS
```
Also add `ARTIFACTS_DIR=/artifacts` to `.env`.

**Warning signs:** Backend logs "NLP artifacts not found" at startup; `/api/recommendations` always returns 503.

### Pitfall 2: scikit-learn Version Mismatch Between Worker and Backend

**What goes wrong:** Worker serializes the `TfidfVectorizer` with scikit-learn 1.8.x. Backend loads it with scikit-learn 1.6.x. joblib/pickle raises `ModuleNotFoundError` or silent data corruption.

**Why it happens:** Different Docker images may install different versions.

**How to avoid:** Pin `scikit-learn>=1.6.0,<2.0.0` in BOTH `worker/requirements.txt` and `backend/requirements.txt`. Verify both Dockerfiles use the same base Python version.

**Warning signs:** `ModuleNotFoundError: No module named 'sklearn.feature_extraction._stop_words'` or `AttributeError` when loading vectorizer.

### Pitfall 3: Memory Overflow During Full Cosine Similarity Matrix Computation

**What goes wrong:** `cosine_similarity(tfidf_matrix)` with N=5000 and `dense_output=True` (default) creates a 5000x5000 float64 matrix = ~200MB in one allocation. With a larger corpus this OOMs.

**Why it happens:** Default `dense_output=True` converts sparse to dense immediately. For 5000 movies it's borderline safe; for 10,000+ it will OOM.

**How to avoid:** Use `cosine_similarity(tfidf_matrix, dense_output=False)` to get a sparse result, then iterate rows:
```python
sim_sparse = cosine_similarity(tfidf_matrix, dense_output=False)
for i in range(N):
    row = np.asarray(sim_sparse[i].todense()).flatten()
```
Or compute similarity in batches of 500 rows using `cosine_similarity(tfidf_matrix[start:end], tfidf_matrix)`.

**Warning signs:** Worker container OOMKilled; `MemoryError` in batch job logs.

### Pitfall 4: `overview` is `None` for Many Movies

**What goes wrong:** TMDB movies with no overview return `None` in the DB. Passing `None` directly to `TfidfVectorizer.fit_transform` raises `TypeError: expected str, bytes or os.PathLike object, not NoneType`.

**Why it happens:** The existing `transform_movie` pipeline stores `None` when TMDB overview is absent (DATA-04 compliant).

**How to avoid:** `preprocess_text` function must coerce `None` to empty string before any text operations:
```python
text = overview or ""
```
Empty strings produce zero-vectors in TF-IDF — those movies will never appear in similarity results (acceptable; they have no content to match).

**Warning signs:** `TypeError` during `fit_transform`; batch job crashes on movie 450 (or similar).

### Pitfall 5: Recommendation Results Missing `overview` (for UI-04)

**What goes wrong:** `MovieSummary` (used by `MovieCard`) does not include `overview`. UI-04 requires displaying "summary" in recommendation results. The `RecommendationItem` endpoint must return `MovieDetail` (which has `overview`) not `MovieSummary`.

**Why it happens:** `MovieCard` was designed for browse, not recommendations. The recommendation response needs the full detail to fulfill UI-04.

**How to avoid:** Return `MovieDetail` (not `MovieSummary`) inside `RecommendationItem`. Or add `overview` to the response payload specifically. `MovieGrid` accepts `MovieSummary[]` so wrap recommendations differently — render explanation + `MovieCard` manually in `RecommendationsPage.tsx` rather than passing to `MovieGrid` directly.

**Warning signs:** Recommendation cards show no summary text despite UI-04 requirement.

### Pitfall 6: React Query POST with `useQuery` (not `useMutation`)

**What goes wrong:** Using `useQuery` for a POST endpoint — React Query will re-execute the query on window focus, component remount, etc., which is expected for GET but unexpected for a POST that could trigger side effects.

**Why it happens:** Developers default to `useQuery` for all API calls.

**How to avoid:** For preference submission (save preferences to DB), use `useMutation`. For fetching recommendations (a stateless POST parameterized by genres/mood), `useQuery` with `enabled` guard is acceptable since the backend is idempotent/read-only. Preference save to backend uses `useMutation`.

---

## Code Examples

Verified patterns from official sources and confirmed working project patterns:

### TF-IDF Vectorizer Configuration (Recommended)
```python
# Source: scikit-learn 1.8.0 docs + content recommendation standard practice
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    max_features=5000,       # Limit vocabulary; reduces memory; captures most relevant terms
    ngram_range=(1, 2),      # Unigrams + bigrams; captures "science fiction", "action thriller"
    stop_words="english",    # Remove common English stop words
    sublinear_tf=True,       # Replace tf with 1+log(tf); dampens very frequent terms
    min_df=2,                # Ignore terms appearing in fewer than 2 documents
)
tfidf_matrix = vectorizer.fit_transform(texts)  # Returns scipy.sparse.csr_matrix (N, 5000)
```

### Cosine Similarity — Row-wise Top-N (Memory-Safe)
```python
# Source: sklearn.metrics.pairwise.cosine_similarity docs + memory-safe pattern
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

TOP_N = 50
N = tfidf_matrix.shape[0]
top_indices = np.zeros((N, TOP_N), dtype=np.int32)

# Process row-by-row to avoid N x N dense matrix
for i in range(N):
    row_vec = tfidf_matrix[i]                          # shape (1, vocab_size) sparse
    sims = cosine_similarity(row_vec, tfidf_matrix).flatten()  # shape (N,)
    sims[i] = 0.0                                      # exclude self
    top_indices[i] = np.argpartition(sims, -TOP_N)[-TOP_N:]   # top-50 positions
```

### Joblib Artifact Persistence
```python
# Source: joblib docs — standard sklearn model persistence
import joblib

# Worker: save
joblib.dump(vectorizer, "/artifacts/tfidf_vectorizer.joblib")
joblib.dump({"tmdb_ids": tmdb_ids, "top_indices": top_indices},
            "/artifacts/similarity_index.joblib")

# Backend startup: load
vectorizer = joblib.load("/artifacts/tfidf_vectorizer.joblib")
sim_data   = joblib.load("/artifacts/similarity_index.joblib")
tmdb_ids   = sim_data["tmdb_ids"]         # list[int], length N
top_indices = sim_data["top_indices"]      # np.ndarray shape (N, 50), dtype int32
```

### FastAPI Recommendations Router
```python
# Source: follows backend/app/api/routes/movies.py pattern exactly
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from app.core.database import get_db

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

class PreferenceRequest(BaseModel):
    genres: list[str]
    mood: str | None = None

@router.post("")
async def get_recommendations(
    body: PreferenceRequest,
    request: Request,
    db=Depends(get_db),
):
    service = RecommendationService(db, request.app.state)
    return await service.get_recommendations(body.genres, body.mood)
```

### React Preference Chip Component Pattern
```typescript
// Follows Tailwind v4 utility class pattern established in project
interface ChipProps {
  label: string;
  selected: boolean;
  onClick: () => void;
  variant?: 'genre' | 'mood';
}

function Chip({ label, selected, onClick, variant = 'genre' }: ChipProps) {
  const base = "px-3 py-1.5 text-sm rounded-full border cursor-pointer transition-colors";
  const active = selected
    ? "bg-blue-600 border-blue-600 text-white"
    : "bg-white border-gray-300 text-gray-700 hover:border-blue-400";
  return (
    <button className={`${base} ${active}`} onClick={onClick} type="button">
      {label}
    </button>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor (async MongoDB) | PyMongo AsyncMongoClient directly | May 2025 (Motor deprecated) | Already adopted in Phase 1 — `[01-01]` decision in STATE.md |
| `@app.on_event("startup")` | `@asynccontextmanager lifespan` | FastAPI 0.93+ (2023) | Already adopted in `main.py` — extend this pattern |
| pickle for sklearn models | joblib.dump/load | 2015+ (stable since) | joblib is faster for numpy arrays, recommended by sklearn docs |
| `dense_output=True` cosine similarity | Row-wise or batched computation | Best practice for N>2000 | Prevents OOM for larger corpora |
| TF-IDF on overview only | TF-IDF on overview + genre names | Recommendation best practice | Genre names in corpus improve content-similarity signal without adding complexity |

**Deprecated/outdated:**
- `sklearn.externals.joblib`: Removed in sklearn 0.23. Use `import joblib` directly (standalone package).
- Motor: Deprecated May 2025, EOL May 2026. Already superseded by pymongo AsyncMongoClient (confirmed in STATE.md).

---

## Open Questions

1. **NLP pipeline run frequency / docker-compose command**
   - What we know: Worker currently runs `ingest_tmdb.py` as the container CMD
   - What's unclear: Should NLP pipeline run automatically after ingestion, or as a separate `docker-compose run worker python jobs/nlp_features.py` command?
   - Recommendation: Run as separate command for now (simpler); sequencing logic is Phase 3+. Planner should create a Wave 0 task to document the run order in README/scripts.

2. **Backend startup behavior when artifacts missing**
   - What we know: FastAPI lifespan loads artifacts if they exist, sets `None` if not
   - What's unclear: Should `/api/recommendations` return 503 or a user-friendly message when artifacts are absent?
   - Recommendation: Return HTTP 503 with `{"detail": "Recommendation engine not ready — run NLP pipeline first"}`. This is an ops concern, not user error.

3. **`overview` in recommendation API response**
   - What we know: `MovieSummary` (used by MovieCard) lacks `overview`; UI-04 requires showing summary
   - What's unclear: Should backend return full `MovieDetail` or extend `RecommendationItem` with an `overview` field?
   - Recommendation: Return `MovieDetail`-equivalent fields inside `RecommendationItem`. Render explanation + card manually in `RecommendationsPage.tsx` — don't pass to `MovieGrid` (which expects `MovieSummary[]` and has no explanation slot).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `backend/pyproject.toml` (`asyncio_mode = "auto"`) and `worker/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command (backend) | `cd backend && pytest tests/test_recommendations.py -x -q` |
| Quick run command (worker) | `cd worker && pytest tests/test_nlp_pipeline.py -x -q` |
| Full suite command | `cd backend && pytest -x -q && cd ../worker && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NLP-01 | `preprocess_text()` strips HTML entities, normalizes whitespace, handles None | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_preprocess_text -x` | Wave 0 |
| NLP-02 | TF-IDF vectorizer produces sparse matrix of correct shape | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_tfidf_vectorizer -x` | Wave 0 |
| NLP-03 | Top-50 similarity index has correct shape (N, 50) and valid int indices | unit | `cd worker && pytest tests/test_nlp_pipeline.py::test_similarity_index -x` | Wave 0 |
| NLP-04 | Explanation string references user-selected genres (not keyword extraction) | unit | `cd backend && pytest tests/test_recommendations.py::test_explanation_format -x` | Wave 0 |
| REC-01 | Recommendation service returns exactly 10 items | unit | `cd backend && pytest tests/test_recommendations.py::test_returns_top_k -x` | Wave 0 |
| REC-02 | Two different genre inputs produce different result sets | integration | `cd backend && pytest tests/test_recommendations.py::test_different_genres_differ -x` | Wave 0 |
| REC-05 | Cold-start user (no history) gets recommendations from genre preferences alone | unit | `cd backend && pytest tests/test_recommendations.py::test_cold_start -x` | Wave 0 |
| UI-02 | Genre chips populated from `/movies/genres`; mood chips show 5 fixed options | manual | N/A — React component test | manual |
| UI-04 | Each recommendation card shows poster, title, year, summary, explanation | manual | N/A — visual verification | manual |
| API-02 | POST /api/recommendations returns 200 with recommendations list | integration | `cd backend && pytest tests/test_recommendations.py::test_endpoint_200 -x` | Wave 0 |
| API-05 | Recommendation endpoint responds in <3s (p95) | smoke | `cd backend && pytest tests/test_recommendations.py::test_response_time -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_recommendations.py -x -q` OR `cd worker && pytest tests/test_nlp_pipeline.py -x -q` (whichever is relevant)
- **Per wave merge:** `cd backend && pytest -x -q && cd ../worker && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `worker/tests/test_nlp_pipeline.py` — covers NLP-01, NLP-02, NLP-03
- [ ] `backend/tests/test_recommendations.py` — covers REC-01, REC-02, REC-05, NLP-04, API-02, API-05
- [ ] `worker/requirements.txt` additions: `scikit-learn>=1.6.0`, `numpy>=2.0.0`, `scipy>=1.17.0`, `joblib>=1.3.0`
- [ ] `backend/requirements.txt` additions: `scikit-learn>=1.6.0`, `numpy>=2.0.0`, `joblib>=1.3.0`
- [ ] `docker-compose.yml` shared volume `nlp_artifacts` for worker + backend
- [ ] `.env` addition: `ARTIFACTS_DIR=/artifacts`

---

## Sources

### Primary (HIGH confidence)
- scikit-learn 1.8.0 docs (PyPI + official docs) — `TfidfVectorizer` parameters, `cosine_similarity`, `joblib.dump`
- Existing project codebase (`main.py`, `conftest.py`, `movie_repo.py`, `ingest_tmdb.py`) — confirmed patterns, existing test infrastructure
- PyPI version records (March 2026) — scikit-learn 1.8.0, numpy 2.4.3, scipy 1.17.1

### Secondary (MEDIUM confidence)
- FastAPI lifespan pattern for ML model loading — multiple confirmed sources (FastAPI official docs + verified community articles)
- joblib vs pickle benchmark characterization — confirmed by joblib official docs + sklearn docs recommendation

### Tertiary (LOW confidence)
- Exact memory footprint for 5000-movie TF-IDF matrix — estimated from dtype math (float32 5000x5000 = 100MB); not benchmarked on this exact corpus

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — scikit-learn/numpy/scipy/joblib are canonical choices; versions confirmed via PyPI
- Architecture: HIGH — all patterns directly derived from existing codebase (lifespan, repo layer, React Query hooks)
- Pitfalls: HIGH for volume/version/OOM (confirmed by docker-compose inspection); MEDIUM for React Query pattern
- NLP hyperparameters: MEDIUM — recommended values are well-established defaults for short text; exact tuning is discretion area

**Research date:** 2026-03-26
**Valid until:** 2026-05-01 (stable domain; scikit-learn API is backward-compatible within 1.x)
