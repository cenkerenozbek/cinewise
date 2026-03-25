# AI-Powered Personalized Movie Recommendation System

## What This Is

A web-based movie recommendation system that uses NLP-based content analysis combined with collaborative filtering to deliver personalized, explainable movie suggestions. The system solves the "cold-start" problem by leveraging semantic content similarity (TF-IDF/embeddings on movie summaries) when users lack interaction history, and progressively blends collaborative signals as users engage. Built as a BAU Computer Engineering capstone project.

## Core Value

Users get accurate, context-aware movie recommendations with transparency ("recommended because...") even on their very first visit, by combining content understanding with explicit preference inputs (mood, genre).

## Requirements

### Validated

- [x] TMDB data ingestion pipeline with MongoDB storage *(Validated in Phase 01)*
- [x] User registration/login with secure password hashing *(Validated in Phase 01)*
- [x] Movie search and filtering (title, genre, year) *(Validated in Phase 01)*
- [x] REST API endpoints (auth, search) *(Validated in Phase 01)*
- [x] Offline batch processing (data ingestion) *(Validated in Phase 01)*
- [x] Graceful error handling for external API failures *(Validated in Phase 01)*

### Active

- [ ] NLP preprocessing and TF-IDF/embedding feature extraction
- [ ] NLP preprocessing and TF-IDF/embedding feature extraction
- [ ] Content-based recommendation using cosine similarity
- [ ] Collaborative filtering signal from user interactions
- [ ] Hybrid scoring with cold-start fallback
- [ ] User registration/login with secure password hashing
- [ ] Preference input (genre, mood) for cold-start users
- [ ] Movie search and filtering (title, genre, year)
- [ ] Recommendation display with poster, summary, and explanation
- [ ] Like/dislike feedback controls
- [ ] REST API endpoints (auth, search, recommendations, feedback)
- [ ] Offline batch processing (data ingestion + NLP features)
- [ ] Graceful error handling for external API failures
- [ ] API response time < 3 seconds (p95) for recommendations
- [ ] Support 10 concurrent users
- [ ] Rate limiting (10 req/min/user)

### Out of Scope

- Video hosting/streaming — copyright and storage constraints
- Mobile native app (iOS/Android) — web-only, responsive design
- Bilingual UI (TR/EN) — COULD in proposal, not MUST
- Real-time chat — not core to recommendation value
- LLM-based inference — too expensive for real-time, using lightweight NLP instead
- Topic modeling (LDA) — COULD, not MUST
- Aspect-based sentiment analysis — COULD, not MUST

## Context

- **Capstone project** for BAU Faculty of Engineering, Computer Engineering dept
- **Team:** Cenk Eren Ozbek (Recommendation & Evaluation), Ibrahim Halil Demircioglu (NLP & Data), Yunus Emre Aydin (Full-Stack & Integration)
- **Advisor:** Asst. Prof. Burak Catalbas
- **Timeline:** 15 weeks (started late — March 25, 2026)
- **Data source:** TMDB API (free tier with rate limits) + MovieLens-20M for offline evaluation
- **Evaluation:** Precision@K, NDCG@K metrics, UAT with university students
- **NLP approach:** Lightweight — TF-IDF or small pretrained embeddings, no LLMs for inference
- **Architecture:** Offline/online separation — batch worker for data ingestion + NLP, FastAPI for serving
- **TMDB API key:** Not yet obtained — needed before data ingestion work begins
- **Database:** MongoDB Atlas free tier (cloud)

## Constraints

- **Tech Stack**: Python/FastAPI (backend), React/TypeScript (frontend), MongoDB, PyTorch/NLTK/spaCy (NLP)
- **Compute**: No GPU guaranteed — prioritize lightweight NLP (TF-IDF, small embeddings)
- **API Rate Limits**: TMDB free tier — caching and batch processing required
- **Budget**: ~2,113 TRY recommended (domain + backend hosting + Colab Pro)
- **Timeline**: 15 weeks, 3 team members working in parallel
- **Privacy**: KVKK compliance — data minimization, hashed passwords, no third-party data sharing
- **Copyright**: No hosted content — only TMDB references (URLs, permitted thumbnails)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid approach (Concept 3) over pure content-based | Best cold-start resilience + high personalization potential | — Pending |
| MongoDB over SQL | Flexible schema for heterogeneous movie metadata | ✓ Confirmed — AsyncMongoClient with upsert semantics working well |
| TF-IDF as primary NLP representation | Lightweight, no GPU needed, good enough for content similarity | — Pending |
| Offline/online architecture split | Keep API response times fast despite heavy NLP processing | ✓ Confirmed — worker runs independently, API stays fast |
| MUST-only scope for v1 | Late start — focus on minimum deliverable first | ✓ Confirmed — Phase 1 delivered full foundation on schedule |
| MongoDB Atlas free tier | Simplest setup, accessible from anywhere, matches proposal | — Pending (using local Docker for now) |
| TMDB v3 api_key param over Bearer header | Bearer requires Read Access Token; api_key works with standard API key | ✓ Confirmed in Phase 01 |

---
## Current State

Phase 01 complete — full monorepo running locally. MongoDB has ~4,300 movies from TMDB. JWT auth, movie browse/search/detail UI all working. Ready for Phase 02 (NLP + content-based recommendations).

*Last updated: 2026-03-25 after Phase 01 completion*
