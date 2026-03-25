# Project Research Summary

**Project:** AI-Powered Personalized Movie Recommendation System
**Domain:** Hybrid Recommender System (Capstone)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

This is a hybrid movie recommendation system capstone that combines content-based filtering (TF-IDF cosine similarity on TMDB plot summaries) with collaborative filtering (neural or user-item matrix from interaction history), served via a FastAPI backend with a React TypeScript frontend and MongoDB Atlas as the data store. The expert-consensus approach for this scale is a strict offline/online separation: heavy ML computation (TMDB ingestion, NLP preprocessing, TF-IDF vectorization, similarity matrix generation) runs in a batch pipeline, while the FastAPI API serves precomputed artifacts at request time with lightweight score blending. This keeps the p95 recommendation response well under 3 seconds without GPU or streaming infrastructure.

The recommended build order is dictated by data dependencies, not feature desirability. MongoDB must be set up before data can be ingested; TMDB ingestion must complete before NLP features can be extracted; TF-IDF artifacts must exist before the recommendation API can serve results. Content-based filtering should be built first and made excellent on its own before adding collaborative filtering, because the live system will have very sparse interaction data relative to academic benchmarks like MovieLens-20M. The most important technical differentiator for this capstone is a smooth cold-start transition: a blending weight alpha that starts at 1.0 (pure content-based) for new users and decreases toward 0.3 as interaction history accumulates.

The primary risks are TF-IDF matrix memory blowup if corpus and vocabulary are not bounded, collaborative filtering producing noise due to interaction sparsity if built before content-based is solid, and TMDB API rate limiting blocking data ingestion if not handled with exponential backoff and append_to_response batching. Cold-start must be treated as three distinct problems (new user, new item, sparse system) rather than one fallback. Auth must be strictly time-boxed to one week to protect time for the recommendation engine, which is the actual grading focus.

## Key Findings

### Recommended Stack

The backend runs on Python 3.12 with FastAPI 0.128.0 and Pydantic 2.12.5, using Beanie 2.0.1 as the async MongoDB ODM. Motor is deprecated (EOL May 2026) — PyMongo 4.16.x's native async API is the successor for any raw MongoDB access. The NLP baseline is scikit-learn 1.8.0 (TF-IDF + cosine similarity) plus NLTK 3.9.2 for text preprocessing; spaCy and sentence-transformers are deferred to Phase 2+ as optional enhancements. PyTorch 2.11.0 CPU-only is required by the project spec for neural collaborative filtering. APScheduler 3.11.2 handles batch job scheduling in-process without needing a Redis or RabbitMQ broker. The frontend is React 19 + TypeScript 5 + Vite 8, with TanStack Query for server state, Zustand for client state, and Tailwind CSS 4 for styling.

**Core technologies:**
- FastAPI 0.128.0: Web framework — async-native, automatic OpenAPI docs, Pydantic integration
- Beanie 2.0.1: MongoDB ODM — async + Pydantic-native, 5-10x throughput vs sync PyMongo
- PyMongo 4.16.x async: Database driver — Motor's replacement, native async API
- scikit-learn 1.8.0: TF-IDF + cosine similarity — battle-tested, CPU-only, zero GPU needed
- NLTK 3.9.2: Text preprocessing — tokenization, stopword removal, lemmatization for TF-IDF input
- PyTorch 2.11.0 (CPU): Neural collaborative filtering — project spec requirement; install CPU-only to avoid 2GB+ CUDA downloads
- APScheduler 3.11.2: Batch scheduling — in-process, no external broker; Celery is overkill for this scale
- React 19 + Vite 8: Frontend — TanStack Query + Zustand replaces Redux with 90% less boilerplate
- httpx: Async HTTP client — TMDB ingestion calls + FastAPI test client; replaces requests in async codebase

### Expected Features

**Must have (table stakes):**
- User registration and login — gates all personalization; bcrypt + JWT; budget max 1 week
- TMDB data ingestion pipeline — populates the entire movie catalog; everything downstream depends on it
- NLP preprocessing + TF-IDF feature extraction — enables content-based similarity; must run before rec API works
- Movie search by title with genre and year filters — basic discovery; without it the system feels like a black box
- Movie detail page (poster, synopsis, genres) — users need context before deciding to watch
- Cold-start onboarding (genre + mood preference quiz) — new users must get useful recommendations on first visit
- Content-based recommendations with cosine similarity — core algorithm; must work standalone before hybrid is built
- Like/dislike feedback — minimum viable interaction signal; binary maximizes participation rate vs star ratings
- Collaborative filtering from accumulated feedback — second algorithm pillar
- Hybrid scoring with cold-start-aware blending — primary technical differentiator; alpha formula is non-negotiable
- Recommendation explanations ("Because you liked...") — academic evaluation criterion; design into scoring pipeline from day one
- Offline evaluation metrics (Precision@K, NDCG@K) — demonstrates academic rigor at capstone defense

**Should have (competitive):**
- Mood-based recommendation entry point (5-8 moods mapped to genre/keyword clusters) — adds discovery dimension beyond genre
- Admin/evaluation dashboard showing metrics visually — better capstone demo
- "More like this" on movie detail page — reuses content similarity, low cost
- Pagination and sorting on search results — polish

**Defer (v2+):**
- Watchlist / watch later — adds CRUD complexity without improving recommendation quality
- Multi-language UI (TR/EN) — doubles UI work; TMDB English metadata is most complete
- Social features (friends, shared lists) — massive scope expansion; zero alignment with core value
- Video trailers / streaming integration — copyright issues, third-party dependencies
- LLM-powered natural language recommendations — API costs, unpredictable outputs, hard to evaluate academically

### Architecture Approach

The system follows a strict offline/online separation. The Batch Worker (Python scripts + APScheduler) fetches TMDB data, runs NLP preprocessing, computes TF-IDF vectors and top-K similarity lookups per movie, and writes artifacts to disk (joblib/npz) and movie metadata to MongoDB. The FastAPI API loads these artifacts into memory at startup via a singleton ModelArtifacts loader and serves recommendations by blending precomputed content scores with collaborative signals read from MongoDB interactions at request time. The React SPA communicates only with FastAPI; it never touches MongoDB or TMDB directly. The Batch Worker never serves user requests.

**Major components:**
1. React SPA — UI rendering, preference capture, feedback input; communicates via REST/JSON to FastAPI only
2. FastAPI API (Online Layer) — auth, movie search, recommendation serving, feedback storage; reads precomputed artifacts from disk and interactions from MongoDB
3. MongoDB Atlas — persistent storage for movies collection, users collection, interactions collection; NOT used to store TF-IDF vectors or similarity matrices
4. Batch Worker (Offline Layer) — TMDB ingestion, NLP preprocessing, TF-IDF fitting, sparse top-K similarity computation, artifact generation; runs on schedule, separate process from API
5. Model Artifacts (Pickle/NPZ on disk) — precomputed TF-IDF vectorizer, TF-IDF matrix, movie_ids index; read-only cache for the API, written by Batch Worker

**Key patterns:**
- Precomputed artifacts with startup loading (singleton pattern in `model_loader.py`)
- Layered FastAPI structure: routes / services / repositories / models / core
- Top-K sparse similarity storage (store top-50 similar movies per movie, not the full N x N matrix)
- Explicit cold-start detection at recommendation time (threshold: 5+ interactions to enter hybrid mode)
- Hybrid blending: `alpha = max(0.3, 1.0 - interaction_count / threshold)`, configurable not hardcoded

### Critical Pitfalls

1. **Cold-start treated as one problem** — There are three distinct scenarios (new user, new item, sparse system). Each needs its own handling. New user: genre+mood onboarding feeds content-based. New item: auto-generate TF-IDF features at ingestion so every movie is recommendable immediately. Test: if two users with different genre preferences get identical top-10, cold-start is broken.

2. **Collaborative filtering built before data exists** — With 10 concurrent live users, the interaction matrix will be ~99.9% sparse. Build content-based first and make it excellent standalone. Pre-seed the database with synthetic interactions from MovieLens-20M for demo purposes. Set hybrid weight heavily toward content-based (80/20) until real interaction data accumulates.

3. **TF-IDF matrix memory blowup** — The full N x N similarity matrix for 50K movies is ~10GB dense. Limit the active corpus to 5K-10K curated movies. Set `max_features=10000` in TfidfVectorizer. Use `scipy.sparse` throughout, never convert to dense. Store only top-50 similar movies per movie, not the full matrix.

4. **TMDB ingestion without rate awareness** — A naive for-loop over movie IDs will hit rate limits and get the IP blocked. Use `append_to_response=credits,keywords` to combine requests. Implement exponential backoff with `Retry-After` header reading. Cache fetched data so re-runs skip already-ingested movies. Target 20-30 req/s, not the maximum.

5. **Explainability bolted on after scoring pipeline** — The scoring function must return `(score, explanation_data)` from day one. Retrofitting traceability after the pipeline is built requires structural changes. Template-based explanations are sufficient: "Similar plot themes to {movie}" or "Popular with fans of {genre}."

## Implications for Roadmap

Based on research, the data dependency chain dictates the phase structure. Content-based must precede collaborative; data ingestion must precede NLP; MongoDB must precede everything. Auth must be time-boxed aggressively to protect recommendation development time.

### Phase 1: Foundation + Data Pipeline

**Rationale:** Nothing else works without data. MongoDB schema, TMDB ingestion, basic auth, and project scaffolding must be in place before any algorithm work can begin. This phase is the critical path bottleneck.
**Delivers:** Running FastAPI + React skeleton, MongoDB connected, TMDB movie catalog ingested (5K-10K movies), basic auth (register/login/JWT), movie search API and UI
**Addresses:** User registration/login, movie search, movie detail page, TMDB ingestion pipeline
**Avoids:** Auth over-engineering (time-box to 1 week), TMDB rate limiting (append_to_response + backoff), missing metadata (quality gates at ingestion), SQL-like MongoDB schema (design around access patterns), storing full TMDB responses (store only needed fields)
**Research flag:** Standard patterns — well-documented FastAPI + MongoDB + JWT auth. No phase research needed.

### Phase 2: Content-Based Recommendation Engine

**Rationale:** Content-based filtering works without any user interaction data, making it the right engine to build first. It also provides the cold-start fallback that makes the system useful from day one. This phase must be complete before collaborative filtering is attempted.
**Delivers:** NLTK preprocessing pipeline, TF-IDF vectorization, sparse top-K similarity computation, artifact generation and startup loading, content-based recommendation API, cold-start onboarding UI (genre + mood preferences), recommendation explanations (designed in from the start)
**Addresses:** NLP/TF-IDF extraction, cold-start onboarding, content-based recommendations, recommendation explanations
**Avoids:** TF-IDF matrix blowup (cap corpus and vocabulary, sparse matrices, top-K only), computing similarity on-the-fly in API path (all NLP is offline), explainability as afterthought (return score + explanation_data from day one)
**Research flag:** Standard patterns for TF-IDF + cosine similarity recommendation. No phase research needed.

### Phase 3: Collaborative Filtering + Hybrid Engine

**Rationale:** Collaborative filtering requires interaction data to be useful. This phase is only viable after Phase 2 produces a working content-based system that generates real user interactions (or pre-seeded MovieLens synthetic data). The hybrid blend is the primary technical differentiator.
**Delivers:** Like/dislike feedback API, interactions collection, PyTorch neural collaborative filtering model (or user-item matrix CF), hybrid blending service with configurable alpha, cold-start detection routing, MovieLens offline evaluation (Precision@K, NDCG@K), temporal train/test split evaluation
**Addresses:** Like/dislike feedback, collaborative filtering, hybrid scoring blend, offline evaluation metrics
**Avoids:** Hardcoded hybrid weights (alpha must be configurable and data-dependent), building CF before data exists (pre-seed with MovieLens if needed), wrong evaluation split (use temporal split, segment by user activity), popularity bias (add diversity penalty if top-10 overlaps >50% across users)
**Research flag:** PyTorch NCF implementation details may benefit from phase research — pattern is documented but implementation specifics vary. Consider `/gsd:research-phase` for the NCF architecture.

### Phase 4: Polish + Evaluation + Demo Prep

**Rationale:** Once all core algorithms work, the final phase focuses on academic rigor demonstration, UX polish, and hardening for the capstone demo under realistic conditions (new users, obscure movies, edge cases).
**Delivers:** Evaluation dashboard (Precision@K, NDCG@K visual display), mood-based recommendation entry point, "More like this" on detail page, rate limiting and error handling, end-to-end UAT with students, demo preparation with edge-case testing
**Addresses:** Mood-based entry point, evaluation dashboard UI, "More like this", API robustness
**Avoids:** Frontend-backend integration delayed to final weeks (integrate continuously from Phase 1), system only working on popular movies (test with obscure movies and new users)
**Research flag:** Standard patterns. No phase research needed.

### Phase Ordering Rationale

- Data before algorithms: MongoDB + TMDB ingestion before NLP before recommendations — enforced by hard data dependencies
- Content before collaborative: TF-IDF engine works standalone; collaborative needs accumulated interaction data that doesn't exist on day one
- Auth time-boxed in Phase 1: it is table stakes but the capstone is graded on recommendation quality; auth must not consume more than 1 week
- Explainability designed in Phase 2: return (score, explanation_data) from the first recommendation function; retrofitting later requires structural rewrite
- Integration is continuous, not a final phase: API contracts (OpenAPI docs) defined in Phase 1; frontend calls real APIs from Phase 2 week 1

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Collaborative Filtering):** PyTorch neural collaborative filtering implementation — the NCF architecture pattern is documented but the specific embedding dimensions, loss functions, and training loop for a sparse capstone-scale dataset need validation. Consider `/gsd:research-phase`.

Phases with standard patterns (skip research-phase):
- **Phase 1:** FastAPI + MongoDB + JWT auth is thoroughly documented with official examples
- **Phase 2:** scikit-learn TF-IDF + cosine similarity for recommendations has extensive tutorials and official docs
- **Phase 4:** Polish and evaluation metrics are well-understood; NDCG@K and Precision@K are standard sklearn metrics

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI, official release notes, and official docs. Motor deprecation confirmed via MongoDB official docs. Vite 8, React Router 7, PyTorch 2.11 all confirmed. |
| Features | HIGH | Feature priorities grounded in academic literature (PMC, IEEE), industry practice (Netflix, Spotify), and explicit capstone requirements. Binary like/dislike vs star ratings is well-evidenced. |
| Architecture | MEDIUM | Offline/online separation pattern is HIGH confidence (IEEE paper, multiple production implementations). Specific FastAPI layering and artifact loading patterns are MEDIUM — sourced from community articles, not official docs. |
| Pitfalls | HIGH | Cold-start, TF-IDF scaling, and TMDB rate limiting pitfalls are well-documented in official sources. Collaboration sparsity pitfall is grounded in academic literature. Evaluation bias pitfall is standard recommendation systems knowledge. |

**Overall confidence:** HIGH

### Gaps to Address

- **PyTorch NCF architecture specifics:** The research recommends PyTorch for collaborative filtering but does not specify embedding dimensions, loss function (BPR vs BCE), or negative sampling strategy for a 5K-10K movie catalog at capstone scale. Address during Phase 3 planning or via `/gsd:research-phase`.
- **Hybrid weight threshold calibration:** The alpha formula (`max(0.3, 1.0 - count/threshold)`) uses a threshold that must be empirically determined based on actual interaction data accumulation rate. Set initially to 20 interactions; adjust after first user testing.
- **MovieLens pre-seeding strategy:** The research recommends pre-seeding the database with synthetic interactions from MovieLens-20M for the demo, but the specific mapping between MovieLens movie IDs and TMDB movie IDs (IMDB ID bridge) needs implementation detail. Validate during Phase 3 planning.
- **KVKK (Turkish data protection) compliance scope:** FEATURES.md notes KVKK requires data minimization for user registration. The scope of compliance requirements for a capstone project vs production deployment is not fully defined. Clarify with the supervising professor.

## Sources

### Primary (HIGH confidence)
- [FastAPI Official Docs](https://fastapi.tiangolo.com/) — JWT auth patterns, async best practices, lifespan events
- [PyMongo Async API](https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/) — v4.16.0 GA, Motor deprecation
- [Motor Deprecation Notice](https://www.mongodb.com/docs/drivers/motor/) — Deprecated May 2025, EOL May 2026
- [scikit-learn TfidfVectorizer Documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) — TF-IDF reference
- [Hybrid Recommendation Architecture (IEEE)](https://ieeexplore.ieee.org/document/9510058/) — offline/online separation pattern
- [Cold Start Problem (Wikipedia)](https://en.wikipedia.org/wiki/Cold_start_(recommender_systems)) — three-way cold start taxonomy
- [PyTorch Releases](https://github.com/pytorch/pytorch/releases) — v2.11.0 confirmed
- [Beanie ODM](https://beanie-odm.dev/) — v2.0.1 on PyPI
- [Pydantic v2.12](https://pydantic.dev/articles/pydantic-v2-12-release) — v2.12.5 stable
- [TMDB Rate Limiting Documentation](https://developer.themoviedb.org/docs/rate-limiting) — rate limits and best practices
- [TMDB Append To Response](https://developer.themoviedb.org/docs/append-to-response) — batching API calls
- [Movie Recommender Systems: Concepts, Methods, Challenges (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9269752/) — academic baseline

### Secondary (MEDIUM confidence)
- [FastAPI Architecture Patterns](https://medium.com/algomart/modern-fastapi-architecture-patterns-for-scalable-production-systems-41a87b165a8b) — layered architecture pattern
- [TF-IDF and Cosine Similarity for Recommendations](https://medium.com/geekculture/understanding-tf-idf-and-cosine-similarity-for-recommendation-engine-64d8b51aa9f9) — content-based approach
- [Hybrid Recommender Systems: A Systematic Literature Review](https://arxiv.org/abs/1901.03888) — hybrid approach rationale
- [Evaluation Metrics for Recommendation Systems](https://weaviate.io/blog/retrieval-evaluation-metrics) — Precision@K, NDCG@K
- [State Management in React 2026](https://www.c-sharpcorner.com/article/state-management-in-react-2026-best-practices-tools-real-world-patterns/) — Zustand + TanStack Query
- [MongoDB Schema Design Anti-Patterns](https://www.mongodb.com/developer/products/mongodb/schema-design-anti-pattern-summary/) — access-pattern-first schema design
- [Vite 8 Announcement](https://vite.dev/blog/announcing-vite8) — Rolldown integration confirmed

### Tertiary (LOW confidence)
- [Filter Bubbles in Recommender Systems](https://arxiv.org/html/2307.01221) — popularity bias mitigation strategies (needs validation against actual system behavior)
- [Model2Vec CPU embeddings](https://dev.to/pringled/model2vec-making-sentence-transformers-500x-faster-on-cpu-and-15x-smaller-3mhe) — Phase 2+ enhancement option for semantic similarity beyond TF-IDF

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
