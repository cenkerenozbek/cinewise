# Domain Pitfalls

**Domain:** AI-Powered Movie Recommendation System (Hybrid: Content-Based + Collaborative Filtering)
**Researched:** 2026-03-25

## Critical Pitfalls

Mistakes that cause rewrites, blown timelines, or fundamentally broken recommendations.

### Pitfall 1: Treating Cold-Start as a Single Problem Instead of Three

**What goes wrong:** Teams build one cold-start solution (e.g., "show popular movies") and assume it covers everything. In reality there are three distinct cold-start scenarios: new user (no interaction history), new item (movie just added with no ratings), and system cold-start (fresh platform with sparse data everywhere). Each requires a different strategy. Showing popular movies to everyone works only if users have similar tastes -- they don't.

**Why it happens:** The proposal says "solve cold-start" without distinguishing the cases. Teams conflate "new user" with "sparse system" and build one fallback path.

**Consequences:** New users get generic recommendations that feel no better than browsing TMDB directly. The system fails to demonstrate its core value proposition -- personalized, explainable recommendations from first visit.

**Prevention:**
- Implement explicit preference onboarding (genre + mood selector) for new users -- this is already in the requirements, make it non-negotiable for the first interaction
- Use content-based similarity (TF-IDF on plot summaries) as the primary engine until collaborative signals accumulate -- do NOT wait for collaborative filtering to "kick in"
- For new items: auto-generate content features from TMDB metadata on ingestion so every movie is recommendable immediately
- Define a clear "confidence threshold" at which the system blends in collaborative signals (e.g., user has rated 5+ movies)

**Detection:** If the recommendation endpoint returns the same top-10 for two different users who selected different genres, the cold-start handling is broken.

**Phase mapping:** Must be addressed in Phase 1 (core recommendation engine). This is the project's primary technical differentiator.

---

### Pitfall 2: Building Collaborative Filtering Before Having Enough Data

**What goes wrong:** Teams invest weeks building matrix factorization or user-user collaborative filtering, then discover it produces garbage results because the user-item interaction matrix is 99.9% sparse. With 10 concurrent users and a few hundred ratings, collaborative filtering has almost nothing to work with.

**Why it happens:** Collaborative filtering sounds impressive in the proposal and academic papers. Students follow tutorials that use MovieLens-20M (20 million ratings) without realizing their live system will have maybe 200 ratings total.

**Consequences:** Wasted development time on a component that won't produce meaningful results during the demo. Collaborative filtering with extreme sparsity recommends random noise. The hybrid blend degrades rather than improves content-based results.

**Prevention:**
- Build content-based recommendation FIRST and make it excellent on its own
- Use MovieLens-20M for offline evaluation of collaborative filtering, but do NOT expect live collaborative filtering to match offline metrics
- Set the hybrid weight to heavily favor content-based (e.g., 80/20) until the system accumulates significant interaction data
- Make the collaborative weight configurable and data-dependent, not hardcoded
- For the capstone demo: pre-seed the database with synthetic user interactions derived from MovieLens so collaborative filtering has something to work with

**Detection:** Run offline evaluation with your actual expected data volume (not MovieLens-scale). If Precision@10 drops below random baseline, collaborative filtering is not ready.

**Phase mapping:** Content-based engine in Phase 1. Collaborative filtering as Phase 2 enhancement. Hybrid blending in Phase 3 after interaction data exists.

---

### Pitfall 3: TF-IDF Matrix Blowup and Stale Similarity Cache

**What goes wrong:** TF-IDF on 10,000+ movie plot summaries produces a massive sparse matrix. Computing all-pairs cosine similarity creates an N x N matrix that grows quadratically. With 50,000 movies, that is a 50K x 50K matrix (~10GB dense). Teams either run out of memory or find that recommendations take 30+ seconds.

**Why it happens:** Tutorials show TF-IDF on 500 movies and it works instantly. Nobody warns you about the quadratic scaling. Additionally, TF-IDF values are relative to the corpus -- adding new movies changes TF-IDF weights for ALL existing movies, invalidating the cached similarity matrix.

**Consequences:** The batch processing pipeline takes hours to complete. API responses exceed the 3-second p95 requirement. Adding new movies requires full recomputation.

**Prevention:**
- Limit the active movie corpus to a curated subset (5,000-10,000 popular/relevant movies) rather than ingesting all of TMDB
- Pre-compute and cache the top-K (e.g., top-50) most similar movies per movie, not the full N x N matrix
- Use scipy.sparse throughout -- never convert to dense
- Set max_features in TfidfVectorizer (e.g., 10,000 terms) to cap vocabulary size
- Use incremental updates: when adding new movies, compute similarity only for new movies against existing corpus, don't recompute everything
- Store pre-computed similarities in MongoDB as a lookup collection

**Detection:** If the batch pipeline takes more than 10 minutes on your development machine, it will be unacceptable in production. Profile memory usage during TF-IDF fitting.

**Phase mapping:** Must be designed correctly in Phase 1 (offline pipeline). Retrofitting a scalable approach later means rewriting the entire similarity computation.

---

### Pitfall 4: TMDB API Ingestion Without Caching or Rate Awareness

**What goes wrong:** Teams make individual API calls for each movie detail, hit rate limits, get IP-blocked, and the data ingestion pipeline takes days to populate the database. Each movie requires at minimum the details endpoint, plus credits, plus keywords -- that is 3 calls per movie without append_to_response optimization.

**Why it happens:** Students build a simple loop: `for movie_id in range(1, 50000): fetch(movie_id)`. No batching, no caching, no error handling for 429 responses. They don't know about `append_to_response` to combine requests.

**Consequences:** Data ingestion takes days instead of hours. IP gets temporarily blocked by TMDB. Incomplete data leads to gaps in the recommendation corpus. Repeated runs re-fetch already-cached data.

**Prevention:**
- Use `append_to_response=credits,keywords,reviews` to get movie details, cast/crew, keywords, and reviews in a single API call (this is free and does not count as extra requests)
- Implement exponential backoff with jitter on 429 responses, reading the `Retry-After` header
- Cache all TMDB responses locally (MongoDB or filesystem) so re-runs skip already-fetched movies
- Use TMDB's `/movie/changes` endpoint to get recently changed movie IDs instead of re-fetching everything
- Respect the practical limit of ~50 requests/second, but target 20-30 req/s to stay safe
- Use TMDB's `/discover/movie` with pagination to get lists of movie IDs efficiently, then fetch details individually

**Detection:** If ingesting 10,000 movies takes more than 2 hours, the pipeline is inefficient. If you see 429 responses in logs, add more backoff.

**Phase mapping:** Phase 1 (data pipeline). Get this right first -- everything downstream depends on having clean, complete data.

---

### Pitfall 5: Ignoring Missing and Inconsistent Movie Metadata

**What goes wrong:** Not all TMDB movies have complete data. Some lack plot summaries (overview field is empty or very short), some have no keywords, some have incorrect genre tags, some have no poster image. TF-IDF on empty strings produces zero vectors, making those movies invisible to content-based recommendations. The system silently drops movies from recommendations without anyone noticing.

**Why it happens:** Teams assume TMDB data is clean and complete because it looks good for popular movies. They never check data quality on the long tail.

**Consequences:** Movies with missing overviews get zero-length TF-IDF vectors and never appear in recommendations. Cosine similarity with zero vectors returns NaN or 0, causing silent failures. Users see gaps: "Why can't I find movie X?" The system's coverage metric drops without explanation.

**Prevention:**
- Define minimum data quality thresholds at ingestion time: overview must be >50 characters, must have at least 1 genre, must have a poster_path
- Build a fallback text for TF-IDF: concatenate title + genres + keywords + cast names when overview is too short
- Log and count filtered-out movies so you know your effective corpus size
- Create a data quality report as part of the batch pipeline output
- Handle NaN/zero vectors explicitly in similarity computation -- filter them out rather than letting them propagate

**Detection:** After ingestion, run: count of movies with empty overview, count with no genres, count with no poster. If >10% of your corpus has missing critical fields, your quality filters need adjustment.

**Phase mapping:** Phase 1 (data pipeline). Data quality gates must exist before NLP processing begins.

---

## Moderate Pitfalls

### Pitfall 6: Explainability as Afterthought

**What goes wrong:** Teams build the recommendation scoring pipeline, get decent Precision@K numbers, then realize they have no idea WHY a movie was recommended. Adding "recommended because you liked X" requires tracking which features drove the score, which means restructuring the scoring pipeline.

**Prevention:**
- Design the recommendation function to return (score, explanation_data) from the start
- For content-based: track which TF-IDF terms overlap between the seed movie and recommendation
- For collaborative: track "users who liked X also liked Y"
- Store explanation metadata alongside recommendation results
- Template-based explanations are fine: "Similar plot themes to {movie_title}" or "Popular with fans of {genre}"

**Detection:** Can you answer "why was this movie recommended?" for every item in a recommendation list? If not, explainability is missing.

**Phase mapping:** Must be baked into the recommendation engine design in Phase 1, not bolted on later.

---

### Pitfall 7: Evaluating with Wrong Metrics or Wrong Data Split

**What goes wrong:** Teams report Precision@10 = 0.85 on MovieLens using random train/test split, then the live system gives terrible recommendations. The offline metrics were inflated because: (a) random split leaks temporal information (future ratings in training), (b) MovieLens users are already engaged movie fans unlike cold-start users, (c) metrics computed on dense users don't reflect sparse-user experience.

**Prevention:**
- Use temporal split for train/test: train on earlier ratings, test on later ones
- Report metrics separately for cold users (< 5 ratings) vs warm users (> 20 ratings)
- Use NDCG@K as primary metric (ranking-aware), not just Precision@K
- Include coverage metric: what percentage of the movie catalog can the system actually recommend?
- Include diversity metric: how different are the top-10 recommendations from each other?
- Be honest in the capstone report about the gap between offline and online performance

**Detection:** If your offline Precision@10 is above 0.7, be suspicious -- check for data leakage or overly favorable evaluation setup.

**Phase mapping:** Evaluation framework design in Phase 2. But decide on metrics and split strategy in Phase 1 planning.

---

### Pitfall 8: Synchronous NLP Processing in the API Path

**What goes wrong:** A user searches for a movie, and the API tries to compute TF-IDF features and similarity on-the-fly. Response times spike to 10-30 seconds. The 3-second p95 requirement is immediately violated.

**Prevention:**
- Strict offline/online separation: ALL NLP computation (TF-IDF fitting, similarity computation) happens in the batch pipeline
- The API only reads pre-computed results from MongoDB
- The API endpoint for recommendations should be a simple MongoDB query + score blending, no scipy/sklearn imports
- If a movie has no pre-computed features (just added), return content-based fallback using metadata features (genre, year, cast) until the next batch run

**Detection:** Import sklearn or scipy in any FastAPI route handler? That is a red flag. Time the recommendation endpoint -- if it exceeds 500ms, something is computing rather than reading.

**Phase mapping:** Architecture decision in Phase 1. This is the core reason for the offline/online split.

---

### Pitfall 9: MongoDB Schema That Doesn't Match Access Patterns

**What goes wrong:** Teams design MongoDB collections like SQL tables -- one collection for movies, one for genres, one for cast, one for keywords -- then join them with $lookup at query time. Or they embed everything in a single bloated document (reviews, all cast members, all similarity scores) creating 16MB+ documents.

**Prevention:**
- Design collections around access patterns, not entity relationships:
  - `movies`: core metadata + embedded genres + top cast (what the UI needs in one read)
  - `movie_features`: TF-IDF vectors and pre-computed similarities (what the recommendation engine needs)
  - `users`: profile + embedded preferences + recent interactions (what auth and personalization need)
  - `interactions`: user-movie events as flat documents (what collaborative filtering reads in bulk)
- Do NOT embed unbounded arrays (all reviews, all similarity pairs) -- use references
- Index the fields you query: `movie_id`, `user_id`, `genre`, `interaction.movie_id`
- Use MongoDB Atlas free tier's 512MB limit as a forcing function -- if your data exceeds it, you are storing too much

**Detection:** If any MongoDB query in the API path takes >100ms, check whether you are doing $lookup or scanning unindexed fields.

**Phase mapping:** Schema design in Phase 1. Changing schema later requires data migration and rewiring all queries.

---

### Pitfall 10: Popularity Bias Creating a Filter Bubble

**What goes wrong:** The system keeps recommending the same 50 popular movies to everyone because they have the most interaction data (collaborative signal) and the most complete metadata (content signal). Less popular but potentially great movies never surface. The recommendation list looks identical for different users.

**Prevention:**
- Add a diversity penalty to the scoring function: penalize movies that appear in too many users' recommendation lists
- Include a "novelty" score component: boost movies the user has NOT seen that are outside their usual genre cluster
- Use genre coverage as a constraint: ensure top-10 recommendations span at least 3 genres
- For content-based: similarity to the user's LEAST liked genre should also be considered (serendipity)
- Log and monitor recommendation diversity metrics during development

**Detection:** Pull the top-10 recommendations for 5 different test users. If overlap exceeds 50%, popularity bias is dominating.

**Phase mapping:** Phase 2-3 enhancement. Get basic recommendations working first, then tune for diversity.

---

## Minor Pitfalls

### Pitfall 11: Not Handling TMDB Image URLs Correctly

**What goes wrong:** TMDB returns poster_path as a relative path (e.g., `/kqjL17yufvn9OVLyXYpvtyrFfak.jpg`). Teams store the full constructed URL (`https://image.tmdb.org/t/p/w500/...`) in the database. TMDB changes their image CDN domain or the team wants a different image size, requiring a full database update.

**Prevention:** Store only the relative `poster_path` from TMDB. Construct the full URL at the API or frontend layer using a configurable base URL. Use appropriate image sizes: `w185` for lists, `w500` for detail views.

**Phase mapping:** Phase 1 (data ingestion). Trivial to get right from the start, painful to fix later.

---

### Pitfall 12: Authentication Complexity Eating Into Recommendation Development Time

**What goes wrong:** Teams spend 2-3 weeks building JWT auth, password reset, email verification, session management -- leaving insufficient time for the actual recommendation engine. Auth is table stakes but is not the capstone differentiator.

**Prevention:**
- Use a minimal auth implementation: bcrypt password hashing + JWT tokens, no email verification for v1
- Budget maximum 1 week for auth (registration, login, token refresh, protected routes)
- Use well-tested libraries (python-jose for JWT, passlib for bcrypt) rather than rolling custom crypto
- Skip "forgot password" for v1 -- it is a COULD feature, not a MUST

**Detection:** If auth work extends past week 2, it is eating into core recommendation development time.

**Phase mapping:** Phase 1, but strictly time-boxed. The capstone is graded on the recommendation system, not on auth.

---

### Pitfall 13: Frontend-Backend Integration Delayed Until Final Weeks

**What goes wrong:** Backend team builds APIs, frontend team builds React UI, they try to connect in the last 2 weeks and discover: API response format doesn't match frontend expectations, CORS issues, authentication flow doesn't work end-to-end, loading states and error handling are missing.

**Prevention:**
- Define API contracts (OpenAPI/Swagger) in Phase 1 before any implementation
- FastAPI generates OpenAPI docs automatically -- use them as the contract
- Frontend should call real APIs from week 3, even if they return mock data initially
- Run end-to-end integration tests weekly, not just before the demo
- Assign one person (Yunus, the full-stack member) as the integration owner throughout

**Detection:** If the frontend is still using hardcoded mock data in week 8, integration is dangerously late.

**Phase mapping:** Continuous from Phase 1. API contract definition is a Phase 1 deliverable.

---

### Pitfall 14: Ignoring MongoDB Atlas Free Tier Limits

**What goes wrong:** MongoDB Atlas M0 free tier has 512MB storage, shared RAM, and limited connections. Teams store raw TMDB responses (including full cast lists, all images, production companies) and hit the storage cap at 5,000 movies. Or they open too many connections from the batch pipeline and the API simultaneously.

**Prevention:**
- Store only fields you actually use: id, title, overview, genres, poster_path, release_date, vote_average, top-5 cast, keywords
- Estimate storage per movie (~2-5KB cleaned) and calculate max corpus size (512MB / 3KB ~ 170K movies -- should be fine for 10K curated movies)
- Use connection pooling (Motor/PyMongo default) and limit batch pipeline connections
- Monitor Atlas dashboard for storage and connection usage weekly
- Consider storing TF-IDF vectors and similarity matrices as files (pickle/parquet) rather than in MongoDB if they push storage limits

**Detection:** Check Atlas dashboard storage usage after initial data load. If >50% full with just movies (no interactions yet), trim your data model.

**Phase mapping:** Phase 1 (data pipeline and schema design).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data ingestion (Phase 1) | TMDB rate limiting and missing data | Use append_to_response, implement quality gates, cache responses |
| NLP pipeline (Phase 1) | TF-IDF matrix memory blowup | Cap vocabulary, limit corpus, use sparse matrices, pre-compute top-K only |
| Content-based engine (Phase 1) | Cold-start treated as single problem | Separate handling for new user, new item, sparse system |
| Schema design (Phase 1) | SQL-like normalization in MongoDB | Design around access patterns, embed what you read together |
| Auth system (Phase 1) | Over-engineering eats timeline | Time-box to 1 week, skip non-essential features |
| Collaborative filtering (Phase 2) | Building CF before having data | Use MovieLens for offline eval, weight content-based heavily in hybrid |
| Evaluation (Phase 2) | Wrong metrics or data split | Temporal split, segment by user activity level, use NDCG@K |
| Hybrid blending (Phase 2-3) | Hardcoded weights | Make weights configurable and data-dependent |
| Explainability (Phase 1-2) | Retrofit after scoring pipeline built | Return (score, explanation) from day one |
| Frontend integration (Phase 2-3) | Late integration failures | Define API contracts early, integrate continuously |
| Demo preparation (Phase 3) | System only works on popular movies | Test with obscure movies, new users, edge cases |

## Sources

- [TMDB Rate Limiting Documentation](https://developer.themoviedb.org/docs/rate-limiting)
- [TMDB Append To Response](https://developer.themoviedb.org/docs/append-to-response)
- [MongoDB Schema Design Anti-Patterns](https://www.mongodb.com/developer/products/mongodb/schema-design-anti-pattern-summary/)
- [MongoDB Unbounded Arrays Anti-Pattern](https://www.mongodb.com/developer/products/mongodb/schema-design-anti-pattern-massive-arrays/)
- [FastAPI Performance Mistakes](https://dev.to/igorbenav/fastapi-mistakes-that-kill-your-performance-2b8k)
- [Cold Start Problem - Things Solver](https://thingsolver.com/blog/the-cold-start-problem/)
- [Cold Start Problem - Tredence](https://www.tredence.com/blog/solving-the-cold-start-problem-in-collaborative-recommender-systems/)
- [Cold Start Problem - FreeCodeCamp](https://www.freecodecamp.org/news/cold-start-problem-in-recommender-systems/)
- [Evaluation Metrics for Recommendation Systems - Weaviate](https://weaviate.io/blog/retrieval-evaluation-metrics)
- [Evaluating Recommendation Systems - Shaped](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)
- [Filter Bubbles in Recommender Systems](https://arxiv.org/html/2307.01221)
- [Movie Recommender Systems: Concepts, Methods, Challenges](https://pmc.ncbi.nlm.nih.gov/articles/PMC9269752/)
- [Movie Recommendation with Machine Learning - Label Your Data](https://labelyourdata.com/articles/movie-recommendation-with-machine-learning)
- [Motor Deprecated in Favor of PyMongo Async](https://www.mongodb.com/developer/products/mongodb/8-fastapi-mongodb-best-practices/)
