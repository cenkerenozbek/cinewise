# Feature Research

**Domain:** AI-Powered Movie Recommendation System (Capstone)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| User registration and login | Users need persistent profiles to receive personalized recommendations; every rec system has auth | LOW | JWT-based auth with bcrypt password hashing. KVKK compliance requires data minimization |
| Movie search and filtering | Users expect to find specific movies by title, genre, year. Without search, the system feels like a black box | MEDIUM | Full-text search on title + genre/year filters. TMDB data must be indexed in MongoDB |
| Movie detail page | Users need poster, synopsis, cast, genre, rating before deciding to watch. Standard in Netflix/TMDB/IMDb | LOW | Render TMDB metadata. Use TMDB image URLs (permitted under API terms). No local hosting of media |
| Personalized recommendations | The entire product premise. Users who sign up expect suggestions tailored to them, not generic popular lists | HIGH | Hybrid engine: content-based (TF-IDF cosine similarity) + collaborative filtering signals blended via weighted scoring |
| Like/dislike feedback | Minimum viable interaction. Users need a way to tell the system what they think. Thumbs up/down is the industry standard (Netflix moved from stars to this) | LOW | Binary feedback stored per user-movie pair. Feeds collaborative filtering signal |
| Recommendation explanations | Users increasingly expect transparency. "Why was this recommended?" is table stakes for trust, especially in academic/capstone contexts where explainability is an evaluation criterion | MEDIUM | Template-based: "Because you liked [Movie X]", "Similar genre/plot to [Movie Y]". Derived from similarity scores and shared features |
| Responsive web UI | Users access from laptop and phone. A non-responsive UI in 2026 is unacceptable | MEDIUM | React with responsive CSS. Desktop-first is fine, but must not break on mobile viewports |
| Cold-start onboarding | New users with no history must still get useful recommendations on first visit. Without this, the product is useless until N interactions | MEDIUM | Explicit preference quiz: select favorite genres and mood. Use these to seed content-based filtering before collaborative data exists |

### Differentiators (Competitive Advantage)

Features that set this capstone project apart from typical rec system implementations.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hybrid scoring with smooth cold-start transition | Most capstone rec systems are pure content-based OR pure collaborative. A hybrid that gracefully shifts weight from content-based to collaborative as user data accumulates is a meaningful technical differentiator | HIGH | Implement a blending weight alpha that starts at 1.0 (100% content-based) and decreases toward 0.5 as the user accumulates ratings. Formula: `alpha = max(0.5, 1 - user_ratings_count / threshold)` |
| NLP-based content similarity (TF-IDF on plot summaries) | Most capstone projects use only genre/tag metadata for content similarity. Extracting TF-IDF vectors from movie plot descriptions enables semantic similarity beyond shallow metadata | MEDIUM | Precompute TF-IDF matrix from TMDB overviews during batch processing. Store sparse vectors in MongoDB. Cosine similarity at query time against precomputed vectors |
| Evaluation metrics dashboard (Precision@K, NDCG@K) | Academic differentiator. Showing quantitative evaluation results demonstrates rigor. Most student projects lack formal evaluation | MEDIUM | Offline evaluation using MovieLens-20M holdout set. Display results in an admin/evaluation page. Not user-facing but critical for capstone defense |
| Mood-based recommendation entry point | Beyond genre selection, letting users pick a mood (e.g., "feel-good", "thought-provoking", "thrilling") adds a discovery dimension. Maps mood keywords to genre/keyword clusters | LOW | Map mood labels to TMDB keyword/genre groups. Use as a filter/boost on top of content similarity. 5-8 predefined moods is sufficient |
| Batch/online architecture separation | Clean separation between offline heavy processing (TMDB ingestion, NLP feature extraction) and online lightweight serving (FastAPI) demonstrates system design maturity | MEDIUM | Batch worker: Python script or scheduled job that ingests TMDB data, computes TF-IDF, stores precomputed features. API server: reads precomputed data, computes final scores in real time |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems, especially given this project's constraints.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Star ratings (1-5 scale) | Seems more granular than like/dislike | Requires more cognitive effort from users, leading to fewer ratings. Netflix abandoned stars for thumbs. With a small user base (10 concurrent), you need maximum participation rate. Cold start is worse with sparse 5-point scales | Binary like/dislike. Simpler, higher participation rate, sufficient signal for collaborative filtering |
| Social features (friends, shared lists) | "Add social to everything" instinct | Massive scope expansion: friend system, privacy controls, feed, notifications. Zero alignment with the core recommendation value. 15-week timeline cannot absorb this | Focus on individual recommendation quality. Social features are a v2+ concern if ever |
| Real-time collaborative filtering updates | Feels modern to update recommendations instantly after every interaction | Requires streaming infrastructure (Kafka, real-time model updates). Overkill for 10 concurrent users. Batch recalculation on login or periodic refresh is sufficient and dramatically simpler | Recompute collaborative scores on user login or on a timer (every 30 min). Users will not notice the difference at this scale |
| LLM-powered natural language recommendations | "Ask the AI what to watch" is trendy | Requires LLM API costs (OpenAI/Anthropic), adds latency, unpredictable outputs, hard to evaluate academically. Contradicts the project's lightweight NLP constraint | Use TF-IDF + cosine similarity for content understanding. Template-based explanations for natural language output. Deterministic, evaluable, free |
| Video trailers / streaming integration | Users might want to watch trailers inline | Copyright issues, external embed complexity, TMDB does not provide trailer hosting. YouTube embeds add third-party dependencies and privacy concerns (KVKK) | Link to TMDB movie page. Users can find trailers themselves. Keep the product focused on discovery, not consumption |
| Watchlist / "watch later" feature | Common in streaming apps | Adds state management complexity (another entity, another CRUD surface, another UI component) without improving recommendation quality. Not in MUST scope | Defer entirely. If needed post-MVP, it is a simple CRUD addition that does not affect the recommendation engine |
| Multi-language support (TR/EN) | Project is for a Turkish university | i18n doubles UI work, requires translated content (TMDB has Turkish data but completeness varies). Explicitly marked as COULD, not MUST in proposal | English-only UI. TMDB English metadata is most complete and consistent. Mention TR support as future work in capstone report |

## Feature Dependencies

```
[User Auth]
    └──requires──> [Database (MongoDB)]

[Movie Search]
    └──requires──> [TMDB Data Ingestion]
                       └──requires──> [Database (MongoDB)]

[Personalized Recommendations]
    └──requires──> [NLP Feature Extraction (TF-IDF)]
    |                  └──requires──> [TMDB Data Ingestion]
    └──requires──> [User Auth] (to identify user)
    └──requires──> [Like/Dislike Feedback] (for collaborative signal)

[Cold-Start Onboarding]
    └──requires──> [User Auth]
    └──requires──> [NLP Feature Extraction] (content-based fallback)

[Recommendation Explanations]
    └──requires──> [Personalized Recommendations] (needs similarity scores)

[Hybrid Scoring Transition]
    └──requires──> [Content-Based Filtering]
    └──requires──> [Collaborative Filtering]
    └──requires──> [Like/Dislike Feedback] (enough data to blend)

[Evaluation Dashboard]
    └──requires──> [Personalized Recommendations] (something to evaluate)
    └──requires──> [MovieLens Data Import] (ground truth for offline eval)
```

### Dependency Notes

- **Personalized Recommendations require NLP Feature Extraction:** Content-based filtering operates on precomputed TF-IDF vectors. These must be batch-processed before the recommendation API can serve results.
- **Cold-Start Onboarding requires NLP Feature Extraction:** Without content features, there is no fallback for users with no interaction history. Genre-only filtering is a degraded fallback if NLP is not ready.
- **Hybrid Scoring requires both filtering approaches:** The blending function needs both content-based and collaborative scores. Content-based can work alone (cold start), but collaborative needs accumulated user feedback.
- **Evaluation Dashboard requires MovieLens import:** TMDB data alone cannot provide ground-truth ratings for offline evaluation. MovieLens-20M provides the rating matrix needed for Precision@K and NDCG@K calculations.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what is needed to demonstrate the capstone.

- [x] User registration/login with hashed passwords -- gates all personalization
- [x] TMDB data ingestion pipeline (batch) -- populates movie catalog
- [x] NLP preprocessing + TF-IDF feature extraction (batch) -- enables content similarity
- [x] Movie search by title with genre/year filters -- basic discovery
- [x] Movie detail page with poster, synopsis, genres -- context for decisions
- [x] Cold-start onboarding (genre + mood preferences) -- first-visit recommendations
- [x] Content-based recommendations with cosine similarity -- core algorithm
- [x] Like/dislike feedback controls -- user interaction signal
- [x] Collaborative filtering from accumulated feedback -- second algorithm pillar
- [x] Hybrid scoring with cold-start-aware blending -- technical differentiator
- [x] Recommendation explanations ("Because you liked...") -- transparency requirement
- [x] Offline evaluation metrics (Precision@K, NDCG@K) -- academic rigor

### Add After Validation (v1.x)

Features to add once core is working, if time permits within the 15-week window.

- [ ] Mood-based recommendation entry point -- enhances discovery UX
- [ ] Admin page showing evaluation metrics visually -- better capstone demo
- [ ] Pagination and sorting on search results -- polish
- [ ] "More like this" on movie detail page -- reuses content similarity, easy win

### Future Consideration (v2+)

Features to defer entirely. Mention as "future work" in capstone report.

- [ ] Watchlist / saved movies -- not core to recommendation quality
- [ ] Multi-language UI (TR/EN) -- doubles UI effort
- [ ] Topic modeling (LDA) on plot descriptions -- COULD, computationally expensive
- [ ] Aspect-based sentiment analysis on reviews -- COULD, requires review data source
- [ ] Mobile native app -- web-responsive is sufficient

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| User auth | HIGH | LOW | P1 |
| TMDB data ingestion | HIGH | MEDIUM | P1 |
| NLP/TF-IDF extraction | HIGH | MEDIUM | P1 |
| Movie search + filters | HIGH | LOW | P1 |
| Movie detail page | HIGH | LOW | P1 |
| Content-based recommendations | HIGH | HIGH | P1 |
| Like/dislike feedback | HIGH | LOW | P1 |
| Cold-start onboarding | HIGH | MEDIUM | P1 |
| Collaborative filtering | HIGH | HIGH | P1 |
| Hybrid scoring blend | HIGH | MEDIUM | P1 |
| Recommendation explanations | MEDIUM | LOW | P1 |
| Evaluation metrics (offline) | MEDIUM | MEDIUM | P1 |
| Mood-based entry point | MEDIUM | LOW | P2 |
| Evaluation dashboard UI | LOW | LOW | P2 |
| "More like this" | MEDIUM | LOW | P2 |
| Watchlist | LOW | LOW | P3 |
| Multi-language | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for capstone delivery
- P2: Should have, add if time permits within 15 weeks
- P3: Nice to have, mention as future work in report

## Competitor Feature Analysis

| Feature | Netflix | Letterboxd | IMDb | Our Approach |
|---------|---------|------------|------|--------------|
| Recommendations | Deep learning, massive data, real-time | Social-driven (friends' ratings) | "More like this" based on metadata | Hybrid TF-IDF + collaborative, lightweight, explainable |
| Cold start | Onboarding quiz + demographic signals | Browse/social discovery | No personalization without account | Genre + mood preference quiz seeds content-based filtering |
| Explanations | "Because you watched X" (brief) | None (social proof instead) | None | Template-based: genre match, plot similarity, user pattern |
| Feedback | Thumbs up/down, % match | Star ratings (0.5-5), reviews | Star ratings (1-10) | Binary like/dislike (maximizes participation) |
| Search | Title, voice, genre browsing | Title, cast, crew, lists | Title, cast, keywords, advanced filters | Title + genre + year filters (sufficient for scope) |
| Evaluation | A/B testing at scale | Community-driven quality | Not applicable | Offline Precision@K, NDCG@K on MovieLens holdout |

## Sources

- [Movie Recommendation Systems: A Business Guide - Stratoflow](https://stratoflow.com/movie-recommendation-system/)
- [Movie Recommender Systems: Concepts, Methods, Challenges - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9269752/)
- [Explainable Movie Recommendation Systems using Story-based Similarity](https://ceur-ws.org/Vol-2068/exss5.pdf)
- [Netflix RecSysOps: Best Practices for Large-Scale Recommender Systems](https://netflixtechblog.medium.com/recsysops-best-practices-for-operating-a-large-scale-recommender-system-95bbe195a841)
- [Inside Spotify's Recommendation System - Music Tomorrow](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide)
- [Hybrid Recommender Systems: A Systematic Literature Review](https://arxiv.org/abs/1901.03888)
- [Top 7 Watchlist UI Features for Cinema Apps - FilmGrail](https://filmgrail.com/blog/top-7-watchlist-ui-features-for-cinema-apps/)
- [Movie Recommendation with Machine Learning - Label Your Data](https://labelyourdata.com/articles/movie-recommendation-with-machine-learning)
- [Recommendation System Design: Step-by-Step Guide](https://www.systemdesignhandbook.com/guides/recommendation-system-design/)

---
*Feature research for: AI-Powered Movie Recommendation System*
*Researched: 2026-03-25*
