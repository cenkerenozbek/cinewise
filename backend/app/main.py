import json
import logging
import os
from contextlib import asynccontextmanager

import joblib
import numpy as np
from fastapi import FastAPI, Request
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


async def _reload_artifacts(app: FastAPI) -> None:
    """Load (or reload) all ML artifacts and catalog cache from disk + DB.

    Called once at startup and again via POST /api/admin/reload whenever the
    worker writes new artifacts so the backend picks up new movies without a
    full container restart.
    """
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")

    # NLP artifacts
    index_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    if os.path.exists(index_path):
        sim_data = joblib.load(index_path)
        app.state.tmdb_ids = sim_data["tmdb_ids"]
        app.state.movie_embeddings = sim_data.get("embeddings")
        app.state.top_indices = sim_data["top_indices"]
        app.state.top_scores = sim_data.get("top_scores")
        app.state.tfidf_vectorizer = None

        embeddings = sim_data.get("embeddings")
        if embeddings is not None:
            try:
                import faiss
                emb = np.asarray(embeddings, dtype=np.float32)
                norms = np.linalg.norm(emb, axis=1, keepdims=True)
                norms[norms == 0.0] = 1.0
                emb_norm = emb / norms
                faiss_index = faiss.IndexFlatIP(emb_norm.shape[1])
                faiss_index.add(emb_norm)
                app.state.faiss_index = faiss_index
                logger.warning("FAISS index built: %d vectors, dim=%d", emb_norm.shape[0], emb_norm.shape[1])
            except Exception as _faiss_err:
                app.state.faiss_index = None
                logger.warning("FAISS index build failed (%s: %s) — history signals limited to top-100 neighbors",
                               type(_faiss_err).__name__, _faiss_err)
        else:
            app.state.faiss_index = None

        logger.info("NLP artifacts loaded")
    else:
        app.state.tfidf_vectorizer = None
        app.state.tmdb_ids = []
        app.state.movie_embeddings = None
        app.state.top_indices = None
        app.state.top_scores = None
        app.state.faiss_index = None
        logger.warning("NLP artifacts not found — recommendations unavailable until worker runs")

    # Catalog cache: {tmdb_id: doc} for all artifact movies — eliminates per-request DB round-trips
    if app.state.tmdb_ids:
        _cc_cursor = app.state.db.movies.find(
            {"tmdb_id": {"$in": list(app.state.tmdb_ids)}},
            {"_id": 0, "tmdb_id": 1, "title": 1, "title_tr": 1, "year": 1,
             "genres": 1, "poster_path": 1, "rating": 1, "overview": 1,
             "vote_count": 1, "adult": 1, "original_language": 1},
        )
        _cc_docs = await _cc_cursor.to_list(length=None)
        app.state.catalog_cache = {doc["tmdb_id"]: doc for doc in _cc_docs}
        logger.warning("Catalog cache built: %d movies", len(app.state.catalog_cache))
    else:
        app.state.catalog_cache = {}

    # CF artifacts
    cf_index_path = os.path.join(artifacts_dir, "cf_index.joblib")
    if os.path.exists(cf_index_path):
        cf_data = joblib.load(cf_index_path)
        app.state.cf_top_indices = cf_data["cf_top_indices"]
        app.state.cf_tmdb_ids = cf_data["tmdb_ids"]
        app.state.cf_top_scores = cf_data.get("cf_top_scores")
        logger.info("CF artifact loaded")
    else:
        app.state.cf_top_indices = None
        app.state.cf_tmdb_ids = []
        app.state.cf_top_scores = None
        logger.info("CF artifact not found — hybrid blending disabled")

    # Evaluation metrics
    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            app.state.metrics = json.load(f)
        logger.info("Metrics artifact loaded")
    else:
        app.state.metrics = None
        logger.info("metrics.json not found — /api/metrics will return 404")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]

    await app.state.db.movies.create_index([("tmdb_id", 1)], unique=True, name="tmdb_id_unique")
    await app.state.db.movies.create_index([("title", "text")])
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])
    await app.state.db.interactions.create_index([("user_id", 1), ("movie_id", 1)], unique=True)
    await app.state.db.interactions.create_index([("user_id", 1)])
    await app.state.db.watchlists.create_index([("user_id", 1), ("movie_id", 1)], unique=True)

    await _reload_artifacts(app)

    yield

    await app.state.mongo_client.close()


app = FastAPI(
    title="AI Movie Recommendation System",
    version="1.0.0",
    lifespan=lifespan,
)

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


@app.post("/api/admin/reload")
async def reload_artifacts(request: Request):
    """Reload ML artifacts and catalog cache without a container restart.

    Called by the worker after writing new artifacts so new movies and updated
    similarity indexes are picked up immediately.
    """
    await _reload_artifacts(request.app)
    return {
        "status": "reloaded",
        "movies": len(request.app.state.catalog_cache),
        "tmdb_ids": len(request.app.state.tmdb_ids),
    }
