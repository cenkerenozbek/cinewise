from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.movies import router as movies_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create async MongoDB client and set indexes
    app.state.mongo_client = AsyncMongoClient(settings.MONGO_URI)
    app.state.db = app.state.mongo_client[settings.DB_NAME]

    # Create text index on movies.title for fast search
    await app.state.db.movies.create_index([("title", "text")])
    # Create compound index on movies.genres + movies.year for filter queries
    await app.state.db.movies.create_index([("genres", 1), ("year", 1)])

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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
