import json
import logging
import os
from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.limiter import limiter
from app.api.routes.auth import router as auth_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.history import router as history_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.movies import router as movies_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.watchlist import router as watchlist_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create async MongoDB client and set indexes
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]

    # Unique index on movies.tmdb_id prevents duplicate ingestion (eval bug 2026-05-10)
    await app.state.db.movies.create_index([("tmdb_id", 1)], unique=True, name="tmdb_id_unique")
    # Create text index on movies.title for fast search
    await app.state.db.movies.create_index([("title", "text")])
    # Create compound index on movies.genres + movies.year for filter queries
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])
    # Create indexes for the interactions collection
    await app.state.db.interactions.create_index([("user_id", 1), ("movie_id", 1)], unique=True)
    await app.state.db.interactions.create_index([("user_id", 1)])
    # Watchlist: unique per (user, movie)
    await app.state.db.watchlists.create_index([("user_id", 1), ("movie_id", 1)], unique=True)

    # Load NLP artifacts for recommendation engine
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    index_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    if os.path.exists(index_path):
        sim_data = joblib.load(index_path)
        app.state.tmdb_ids = sim_data["tmdb_ids"]
        app.state.top_indices = sim_data["top_indices"]
        # top_scores is present in new-format artifacts (sentence-transformers);
        # absent in old TF-IDF artifacts — service falls back to frequency count
        app.state.top_scores = sim_data.get("top_scores")
        app.state.tfidf_vectorizer = None  # no longer used at runtime
        logger.info("NLP artifacts loaded at startup")
    else:
        app.state.tfidf_vectorizer = None
        app.state.tmdb_ids = []
        app.state.top_indices = None
        app.state.top_scores = None
        logger.warning("NLP artifacts not found — recommendations unavailable until worker runs")

    # Load CF artifacts for hybrid blending
    cf_index_path = os.path.join(artifacts_dir, "cf_index.joblib")
    if os.path.exists(cf_index_path):
        cf_data = joblib.load(cf_index_path)
        app.state.cf_top_indices = cf_data["cf_top_indices"]
        app.state.cf_tmdb_ids = cf_data["tmdb_ids"]
        app.state.cf_top_scores = cf_data.get("cf_top_scores")
        logger.info("CF artifact loaded at startup")
    else:
        app.state.cf_top_indices = None
        app.state.cf_tmdb_ids = []
        app.state.cf_top_scores = None
        logger.info("CF artifact not found — hybrid blending disabled")

    # Load evaluation metrics artifact
    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            app.state.metrics = json.load(f)
        logger.info("Metrics artifact loaded at startup")
    else:
        app.state.metrics = None
        logger.info("metrics.json not found — /api/metrics will return 404")

    yield

    # Shutdown: close MongoDB connection
    app.state.mongo_client.close()


app = FastAPI(
    title="AI Movie Recommendation System",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting — must be configured before adding SlowAPIMiddleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(feedback_router)
app.include_router(history_router)
app.include_router(metrics_router)
app.include_router(movies_router)
app.include_router(recommendations_router)
app.include_router(watchlist_router)


@app.get("/")
async def root():
    return {
        "name": "CineWise API",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
