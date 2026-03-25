# Architecture Patterns

**Domain:** AI-Powered Hybrid Movie Recommendation System
**Researched:** 2026-03-25

## Recommended Architecture

The system follows an **offline/online separation pattern** -- the most proven architecture for recommendation systems at this scale. Heavy computation (data ingestion, NLP feature extraction, similarity matrix computation) runs offline in batch jobs. The FastAPI API serves precomputed results with lightweight online scoring.

### System Overview

```
+------------------+       +-------------------+       +------------------+
|                  |       |                   |       |                  |
|   React SPA      | <---> |   FastAPI API      | <---> |   MongoDB        |
|   (Client)       |  REST |   (Online Layer)   |       |   (Data Store)   |
|                  |       |                   |       |                  |
+------------------+       +--------+----------+       +--------+---------+
                                    |                           |
                                    | loads                     | reads/writes
                                    v                           |
                           +--------+----------+               |
                           |                   |               |
                           |  Model Artifacts  | <-------------+
                           |  (Pickle/Joblib)  |       +-------+--------+
                           |                   |       |                |
                           +-------------------+       |  Batch Worker  |
                                    ^                  |  (Offline)     |
                                    | generates        |                |
                                    |                  +-------+--------+
                                    +---------------------------+
                                                               |
                                                               | fetches
                                                               v
                                                      +--------+--------+
                                                      |                 |
                                                      |   TMDB API      |
                                                      |   (External)    |
                                                      |                 |
                                                      +-----------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Technology |
|-----------|---------------|-------------------|------------|
| **React SPA** | UI rendering, user interactions, preference capture | FastAPI API (REST/JSON) | React, TypeScript, Axios |
| **FastAPI API** | Auth, search, recommendation serving, feedback capture | MongoDB, Model Artifacts | FastAPI, Pydantic, PyJWT |
| **MongoDB** | Persistent storage for movies, users, interactions | FastAPI API, Batch Worker | MongoDB Atlas (free tier) |
| **Batch Worker** | TMDB ingestion, NLP preprocessing, similarity computation | MongoDB, TMDB API, Model Artifacts | Python scripts, APScheduler or cron |
| **Model Artifacts** | Precomputed TF-IDF vectorizer, similarity matrix, feature vectors | Read by FastAPI API, written by Batch Worker | Pickle/Joblib files on disk |
| **TMDB API** | Movie metadata source (titles, summaries, genres, posters) | Batch Worker only | HTTPS, rate-limited |

### Strict Boundary Rules

1. **The React SPA never talks to MongoDB or TMDB directly.** All data flows through FastAPI.
2. **The FastAPI API never calls TMDB.** TMDB data is pre-ingested by the Batch Worker.
3. **The Batch Worker never serves user requests.** It only writes to MongoDB and generates artifacts.
4. **Model Artifacts are a read-only cache for the API.** The API loads them at startup; the Batch Worker regenerates them on schedule.

## Data Flow

### Flow 1: Data Ingestion (Offline)

```
TMDB API --> Batch Worker --> MongoDB (movies collection)
                |
                +--> NLP Pipeline (tokenize, clean, TF-IDF) --> Model Artifacts
                |
                +--> Precomputed similarity matrix --> Model Artifacts
```

**Steps:**
1. Batch Worker fetches movie data from TMDB API (paginated, respecting rate limits)
2. Raw movie data stored in MongoDB `movies` collection
3. NLP pipeline processes movie overviews/descriptions:
   - Text cleaning (lowercase, remove stopwords, lemmatize)
   - TF-IDF vectorization across all movie overviews
   - Cosine similarity matrix computation
4. Artifacts saved: TF-IDF vectorizer (pickle), TF-IDF matrix (sparse matrix), similarity scores (precomputed top-N per movie)

### Flow 2: Cold-Start Recommendation (Online)

```
User (new) --> React SPA --> POST /preferences {genres, mood}
                                    |
                                    v
                             FastAPI API
                                    |
                                    +--> Query MongoDB for movies matching genres/mood
                                    +--> Load similarity matrix from artifacts
                                    +--> Score candidates using content similarity
                                    +--> Return top-K with explanations
                                    |
                                    v
                             React SPA <-- [{movie, score, explanation}]
```

**Cold-start strategy:** When a user has no interaction history, use their stated preferences (genre, mood) to find seed movies, then use content-based similarity (TF-IDF cosine similarity) to expand recommendations. Explanation: "Recommended because you like [genre] and this is similar to [seed movie]."

### Flow 3: Hybrid Recommendation (Online, Returning User)

```
User (returning) --> React SPA --> GET /recommendations
                                          |
                                          v
                                   FastAPI API
                                          |
                                          +--> Fetch user interaction history from MongoDB
                                          +--> Content score: similarity to liked movies (from artifacts)
                                          +--> Collaborative score: user-item matrix (from MongoDB interactions)
                                          +--> Hybrid score = alpha * content + (1-alpha) * collaborative
                                          |    (alpha decreases as interaction count grows)
                                          +--> Return top-K with explanations
                                          |
                                          v
                                   React SPA <-- [{movie, score, explanation}]
```

**Hybrid blending formula:**
- `alpha = max(0.3, 1.0 - (interaction_count / threshold))`
- New users: alpha ~ 1.0 (pure content-based)
- Active users: alpha ~ 0.3 (mostly collaborative, still some content)
- This is a simple weighted hybrid -- appropriate for capstone scope

### Flow 4: User Feedback Loop

```
User clicks like/dislike --> React SPA --> POST /feedback {movie_id, action}
                                                 |
                                                 v
                                          FastAPI API
                                                 |
                                                 +--> Store in MongoDB (interactions collection)
                                                 +--> (Optional) Update in-memory user profile
```

Feedback is stored immediately but does not trigger model retraining. The collaborative signal updates naturally on next recommendation request by reading from the interactions collection.

## Patterns to Follow

### Pattern 1: Precomputed Artifacts with Startup Loading

**What:** Compute expensive ML artifacts offline. Load them into memory when the FastAPI server starts. Serve recommendations from memory.

**When:** Always for this project. TF-IDF matrix and similarity scores are too expensive to compute per-request.

**Why:** Keeps API response time under 3 seconds (the p95 requirement). A precomputed similarity lookup is O(1) per movie.

**Example:**
```python
# app/core/model_loader.py
import joblib
from scipy.sparse import load_npz

class ModelArtifacts:
    _instance = None

    @classmethod
    def load(cls, artifacts_dir: str):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.vectorizer = joblib.load(f"{artifacts_dir}/tfidf_vectorizer.joblib")
            cls._instance.tfidf_matrix = load_npz(f"{artifacts_dir}/tfidf_matrix.npz")
            cls._instance.movie_ids = joblib.load(f"{artifacts_dir}/movie_ids.joblib")
        return cls._instance

# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    ModelArtifacts.load("./artifacts")
    yield

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Layered FastAPI Backend

**What:** Separate concerns into layers: routes (controllers), services (business logic), repositories (data access).

**When:** Always. Keeps recommendation logic testable and independent of HTTP concerns.

**Example structure:**
```
backend/
  app/
    api/
      routes/
        auth.py          # POST /register, POST /login
        movies.py         # GET /movies, GET /movies/search
        recommendations.py # GET /recommendations
        feedback.py       # POST /feedback
    services/
      auth_service.py
      movie_service.py
      recommendation_service.py   # Hybrid scoring logic lives here
      content_recommender.py      # TF-IDF similarity
      collaborative_recommender.py # User-item interactions
    repositories/
      user_repository.py
      movie_repository.py
      interaction_repository.py
    models/
      user.py
      movie.py
      interaction.py
    core/
      config.py
      security.py        # JWT, password hashing
      model_loader.py     # Artifact loading singleton
    main.py
```

### Pattern 3: Sparse Similarity Storage (Top-N per Movie)

**What:** Do NOT store the full N x N similarity matrix. For 10,000 movies, that is 100M entries. Instead, precompute and store only the top-K (e.g., top-50) most similar movies per movie.

**When:** Always. Full matrix does not fit in memory for large catalogs and is wasteful.

**Storage format:**
```python
# Precompute and save as dict: {movie_id: [(similar_id, score), ...]}
# Or as MongoDB document:
{
    "movie_id": "tt1234567",
    "similar": [
        {"movie_id": "tt7654321", "score": 0.87},
        {"movie_id": "tt9876543", "score": 0.82},
        # ... top 50
    ]
}
```

### Pattern 4: Explicit Cold-Start Detection

**What:** Check interaction count at recommendation time. Route to content-based vs hybrid pipeline explicitly.

**When:** Every recommendation request.

```python
# services/recommendation_service.py
async def get_recommendations(user_id: str) -> list[Recommendation]:
    interactions = await interaction_repo.get_by_user(user_id)

    if len(interactions) < COLD_START_THRESHOLD:  # e.g., 5
        return await content_recommender.recommend(
            user_id, preferences=await user_repo.get_preferences(user_id)
        )
    else:
        content_scores = await content_recommender.score(user_id, interactions)
        collab_scores = await collaborative_recommender.score(user_id, interactions)
        alpha = max(0.3, 1.0 - len(interactions) / BLEND_THRESHOLD)
        return blend(content_scores, collab_scores, alpha)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Computing Similarity On-the-Fly

**What:** Running TF-IDF vectorization and cosine similarity at request time.
**Why bad:** TF-IDF vectorization of a corpus is O(n*m) where n=documents, m=vocabulary. For 10K movies, this takes seconds. Doing it per-request will blow the 3s p95 budget and crash under 10 concurrent users.
**Instead:** Precompute offline, load at startup.

### Anti-Pattern 2: Storing TF-IDF Vectors in MongoDB

**What:** Saving dense/sparse TF-IDF vectors as MongoDB documents.
**Why bad:** MongoDB is not optimized for vector operations. Reading, deserializing, and computing similarity across thousands of documents from MongoDB is slow and fragile. Document size limits (16MB) also become a concern.
**Instead:** Store artifacts as files (joblib/pickle/npz). Load into memory. Use MongoDB for metadata and interactions only.

### Anti-Pattern 3: Monolithic Worker-and-Server Process

**What:** Running the batch worker and the API server in the same process.
**Why bad:** A long-running TMDB ingestion job will block the event loop or starve API requests of resources. Memory spikes during NLP processing can crash the API.
**Instead:** Run the batch worker as a separate process (cron job, separate script). It writes to MongoDB and artifact files. The API server reads from them.

### Anti-Pattern 4: Real-Time Model Retraining on Feedback

**What:** Retraining TF-IDF or updating the similarity matrix every time a user likes/dislikes a movie.
**Why bad:** Unnecessary complexity for a capstone. The content features (movie overviews) do not change with user feedback. Collaborative signals can be read from MongoDB interactions at request time without retraining.
**Instead:** Batch-retrain on schedule (e.g., daily or weekly). Content features only change when new movies are added.

## MongoDB Collection Design

```
movies
  _id: ObjectId
  tmdb_id: int (indexed, unique)
  title: string
  overview: string
  genres: [string]
  release_date: string
  poster_path: string
  vote_average: float
  popularity: float
  keywords: [string]
  processed: boolean       # Has NLP been run?

users
  _id: ObjectId
  email: string (indexed, unique)
  password_hash: string
  preferences:
    genres: [string]
    mood: string
  created_at: datetime

interactions
  _id: ObjectId
  user_id: ObjectId (indexed)
  movie_id: ObjectId (indexed)
  action: "like" | "dislike" | "view"
  timestamp: datetime
  # Compound index: (user_id, movie_id) unique
```

## Scalability Considerations

| Concern | At 10 users (capstone) | At 1K users | At 100K users |
|---------|----------------------|-------------|---------------|
| **Movie catalog** | 5K-10K movies, full similarity in memory | 50K movies, top-N sparse similarity | Vector DB (Milvus/Pinecone), ANN search |
| **Collaborative filtering** | In-memory user-item matrix from MongoDB | Precomputed user similarity, cached | Matrix factorization (SVD), model serving |
| **API serving** | Single FastAPI instance | Uvicorn workers (2-4) | Horizontal scaling, load balancer |
| **Batch processing** | Manual trigger or cron | Celery + Redis task queue | Airflow/Prefect DAG orchestration |
| **Model artifacts** | Local filesystem | Shared filesystem / S3 | Model registry (MLflow) |

For this capstone project, the "10 users" column is the target. The architecture is designed to be clean enough to scale, but optimization beyond this tier is out of scope.

## Suggested Build Order (Dependencies)

Build order is dictated by data dependencies -- you cannot recommend movies you have not ingested.

```
Phase 1: Foundation
  MongoDB setup + schemas
  FastAPI skeleton with health check
  React SPA skeleton with routing
  Basic auth (register/login/JWT)

Phase 2: Data Pipeline
  TMDB API integration (batch worker)
  Movie ingestion into MongoDB          # Requires: MongoDB setup
  Movie browsing/search API + UI        # Requires: movies in DB

Phase 3: Content Recommendation Engine
  NLP pipeline (text cleaning, TF-IDF)  # Requires: movies in DB
  Similarity matrix computation         # Requires: TF-IDF vectors
  Artifact generation + loading         # Requires: similarity matrix
  Content-based recommendation API      # Requires: artifacts loaded
  Preference input UI (cold-start)      # Requires: recommendation API

Phase 4: Hybrid + Feedback
  Feedback API (like/dislike)           # Requires: auth + movies
  Interaction storage                   # Requires: MongoDB interactions schema
  Collaborative filtering signal        # Requires: interaction data
  Hybrid blending logic                 # Requires: content + collaborative
  Cold-start detection + routing        # Requires: hybrid logic

Phase 5: Polish + Evaluation
  Recommendation explanations UI        # Requires: hybrid API
  Precision@K / NDCG@K evaluation       # Requires: working recommendations
  Rate limiting, error handling         # Requires: all APIs functional
  UAT with students                     # Requires: deployed system
```

**Critical path:** MongoDB -> TMDB ingestion -> NLP/TF-IDF -> Similarity -> Recommendation API. Everything else can proceed in parallel once data exists.

## Sources

- [FastAPI Architecture Patterns](https://medium.com/algomart/modern-fastapi-architecture-patterns-for-scalable-production-systems-41a87b165a8b) - MEDIUM confidence
- [Deploying Recommendation System with FastAPI](https://blog.xmartlabs.com/blog/deploying-a-recommendation-system-using-fastapi-tf-serving-and-feast/) - MEDIUM confidence
- [FastAPI sklearn Serving Pattern](https://github.com/nickc1/sklearn_fastapi) - MEDIUM confidence
- [Hybrid Recommendation Architecture (IEEE)](https://ieeexplore.ieee.org/document/9510058/) - HIGH confidence
- [Cold Start Problem (Wikipedia)](https://en.wikipedia.org/wiki/Cold_start_(recommender_systems)) - HIGH confidence
- [TF-IDF and Cosine Similarity for Recommendations](https://medium.com/geekculture/understanding-tf-idf-and-cosine-similarity-for-recommendation-engine-64d8b51aa9f9) - MEDIUM confidence
- [scikit-learn TfidfVectorizer Documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) - HIGH confidence
- [Layered FastAPI Architecture](https://dev.to/markoulis/layered-architecture-dependency-injection-a-recipe-for-clean-and-testable-fastapi-code-3ioo) - MEDIUM confidence
