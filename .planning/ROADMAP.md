# Roadmap: AI-Powered Personalized Movie Recommendation System

## Overview

The build order is dictated by data dependencies, not feature desirability. MongoDB and TMDB ingestion must exist before NLP processing can run; TF-IDF artifacts must exist before recommendations can be served; content-based recommendations must be solid before collaborative filtering is layered in. The four phases follow this hard dependency chain: foundation and data pipeline first, then content-based engine, then collaborative and hybrid engine, then evaluation hardening and demo preparation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation and Data Pipeline** - Project scaffold, MongoDB, TMDB ingestion, auth, and movie search
- [ ] **Phase 2: Content-Based Recommendation Engine** - NLP preprocessing, TF-IDF, similarity index, cold-start onboarding, and explainable recommendations
- [ ] **Phase 3: Collaborative Filtering and Hybrid Engine** - Like/dislike feedback, collaborative filtering, hybrid blending, and system hardening
- [ ] **Phase 4: Evaluation and Demo Preparation** - Offline evaluation metrics, UAT, performance validation, and capstone demo hardening

## Phase Details

### Phase 1: Foundation and Data Pipeline
**Goal**: Users can browse and search a real movie catalog, and developers can authenticate against a running backend connected to MongoDB
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-04, DATA-05, DATA-06, UI-01, UI-03, API-01, API-04, API-06, SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. A new user can register an account and log in; their credentials are stored with bcrypt hashing in MongoDB
  2. A logged-in user can search movies by title and filter by genre or year; results return within 2 seconds
  3. The offline batch pipeline ingests TMDB movie metadata (title, year, genres, cast, director, summary, poster URL, rating, vote count, and Turkish title when available) and completes within 2 hours for the target dataset
  4. Missing metadata fields in TMDB responses do not crash the ingestion pipeline or break search results
  5. TMDB API failures trigger retry with exponential backoff; the system does not lose already-ingested data
**Plans:** 4/4 plans executed

Plans:
- [x] 01-01-PLAN.md — Project scaffold, Docker Compose, shared models, configuration
- [x] 01-02-PLAN.md — FastAPI backend with JWT auth and movie search/browse API
- [x] 01-03-PLAN.md — TMDB batch ingestion worker pipeline
- [x] 01-04-PLAN.md — React frontend with auth, movie grid, search, filters, detail page

### Phase 2: Content-Based Recommendation Engine
**Goal**: Any user — including a brand-new visitor — gets personalized, explainable movie recommendations on their first session
**Depends on**: Phase 1
**Requirements**: NLP-01, NLP-02, NLP-03, NLP-04, REC-01, REC-02, REC-05, UI-02, UI-04, API-02, API-05
**Success Criteria** (what must be TRUE):
  1. A new user who selects genre preferences and an optional mood receives a Top-K recommendation list tailored to those preferences within 3 seconds
  2. Each recommended movie displays its poster, title, year, summary, and a human-readable explanation of why it was recommended
  3. Two new users with different genre preferences receive meaningfully different recommendation lists (cold-start is not a single static list)
  4. The NLP batch pipeline preprocesses movie summaries, builds TF-IDF vectors, and writes a precomputed top-50 similarity index to disk without running out of memory
  5. The recommendation API loads precomputed artifacts at startup and serves responses within 3 seconds (p95) without recomputing NLP on each request
**Plans:** 1/4 plans executed

Plans:
- [ ] 02-01-PLAN.md — Infrastructure: NLP dependencies, shared volume, type contracts, test scaffolds
- [ ] 02-02-PLAN.md — NLP batch pipeline: text preprocessing, TF-IDF vectorization, similarity index
- [ ] 02-03-PLAN.md — Recommendation API: service, repository, router, artifact loading
- [ ] 02-04-PLAN.md — Frontend: preference chips, recommendations page, navbar, routing

### Phase 3: Collaborative Filtering and Hybrid Engine
**Goal**: Returning users receive recommendations that improve based on their like/dislike history, and the system blends collaborative and content signals intelligently
**Depends on**: Phase 2
**Requirements**: DATA-03, REC-03, REC-04, UI-05, API-03, API-07, SEC-03
**Success Criteria** (what must be TRUE):
  1. A logged-in user can like or dislike any recommended movie; that interaction is persisted in MongoDB
  2. A returning user with 5 or more interactions receives recommendations that differ from what a new user with the same genre preferences would see, demonstrating collaborative signal influence
  3. The hybrid blending weight shifts automatically from pure content-based (alpha=1.0) toward collaborative signal as a user accumulates interactions, with a configurable threshold
  4. The system rejects requests exceeding 10 per minute per user with a rate-limit response, and sustains correct behavior under 10 concurrent users
**Plans**: TBD

### Phase 4: Evaluation and Demo Preparation
**Goal**: The system demonstrates measurable recommendation quality using standard academic metrics and handles realistic demo conditions without failure
**Depends on**: Phase 3
**Requirements**: (none — this phase addresses capstone evaluation obligations from PROJECT.md: Precision@K, NDCG@K metrics, UAT with university students)
**Success Criteria** (what must be TRUE):
  1. Precision@K and NDCG@K scores are computed against a held-out evaluation set and displayed in the running application or a script output
  2. At least 5 university students complete a UAT session without encountering a system crash or unhandled error
  3. All three cold-start scenarios (new user, obscure movie with few interactions, sparse system with few total interactions) produce valid recommendation results rather than empty lists or errors
  4. A full demo walkthrough — new user registration, preference selection, recommendation display, like/dislike feedback, returning user session — completes end-to-end without manual intervention
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Data Pipeline | 4/4 | Complete | 2026-03-25 |
| 2. Content-Based Recommendation Engine | 1/4 | In Progress|  |
| 3. Collaborative Filtering and Hybrid Engine | 0/TBD | Not started | - |
| 4. Evaluation and Demo Preparation | 0/TBD | Not started | - |
