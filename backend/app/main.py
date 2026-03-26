import logging
import os
from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.movies import router as movies_router
from app.api.routes.recommendations import router as recommendations_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create async MongoDB client and set indexes
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]

    # Create text index on movies.title for fast search
    await app.state.db.movies.create_index([("title", "text")])
    # Create compound index on movies.genres + movies.year for filter queries
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])

    # Load NLP artifacts for recommendation engine
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    vectorizer_path = os.path.join(artifacts_dir, "tfidf_vectorizer.joblib")
    index_path = os.path.join(artifacts_dir, "similarity_index.joblib")
    if os.path.exists(vectorizer_path) and os.path.exists(index_path):
        app.state.tfidf_vectorizer = joblib.load(vectorizer_path)
        sim_data = joblib.load(index_path)
        app.state.tmdb_ids = sim_data["tmdb_ids"]
        app.state.top_indices = sim_data["top_indices"]
        logger.info("NLP artifacts loaded at startup")
    else:
        app.state.tfidf_vectorizer = None
        app.state.tmdb_ids = []
        app.state.top_indices = None
        logger.warning("NLP artifacts not found — recommendations unavailable until worker runs")

    yield

    # Shutdown: close MongoDB connection
    app.state.mongo_client.close()


app = FastAPI(
    title="AI Movie Recommendation System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(movies_router)
app.include_router(recommendations_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
