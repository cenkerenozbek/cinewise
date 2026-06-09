"""
Test configuration and fixtures for the backend API tests.

Uses mongomock for an in-memory MongoDB and overrides the FastAPI app's
get_db dependency so no real MongoDB connection is needed.
"""
import pytest
import pytest_asyncio
import mongomock
import numpy as np
from httpx import AsyncClient, ASGITransport
from fastapi import Request

from app.main import app
from app.core.database import get_db


class AsyncCollection:
    """Thin async wrapper around a mongomock Collection.

    Converts mongomock's synchronous methods into coroutines so that
    repository code using `await collection.find_one(...)` works during tests.
    """

    def __init__(self, collection):
        self._col = collection

    async def find_one(self, filter=None, *args, **kwargs):
        return self._col.find_one(filter, *args, **kwargs)

    def find(self, filter=None, *args, **kwargs):
        return AsyncCursor(self._col.find(filter, *args, **kwargs))

    async def insert_one(self, document, *args, **kwargs):
        return self._col.insert_one(document, *args, **kwargs)

    async def insert_many(self, documents, *args, **kwargs):
        return self._col.insert_many(documents, *args, **kwargs)

    async def update_one(self, filter, update, *args, **kwargs):
        return self._col.update_one(filter, update, *args, **kwargs)

    async def delete_many(self, filter, *args, **kwargs):
        return self._col.delete_many(filter, *args, **kwargs)

    async def count_documents(self, filter, *args, **kwargs):
        return self._col.count_documents(filter, *args, **kwargs)

    async def distinct(self, key, filter=None, *args, **kwargs):
        return self._col.distinct(key, filter, *args, **kwargs)

    async def create_index(self, keys, *args, **kwargs):
        # mongomock create_index is synchronous
        return self._col.create_index(keys, *args, **kwargs)


class AsyncCursor:
    """Thin async wrapper around a mongomock Cursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def skip(self, n):
        self._cursor = self._cursor.skip(n)
        return self

    def limit(self, n):
        self._cursor = self._cursor.limit(n)
        return self

    def sort(self, key_or_list, direction=None):
        if direction is not None:
            self._cursor = self._cursor.sort(key_or_list, direction)
        else:
            self._cursor = self._cursor.sort(key_or_list)
        return self

    async def to_list(self, length=None):
        results = list(self._cursor)
        if length is not None:
            return results[:length]
        return results


class AsyncDatabase:
    """Thin async wrapper around a mongomock Database."""

    def __init__(self, db):
        self._db = db

    def __getitem__(self, name):
        return AsyncCollection(self._db[name])

    def __getattr__(self, name):
        # Allow attribute-style access like db.movies
        if name.startswith("_"):
            raise AttributeError(name)
        return AsyncCollection(self._db[name])


@pytest_asyncio.fixture
async def test_db():
    """Create a fresh in-memory mongomock database for each test."""
    client = mongomock.MongoClient()
    db = AsyncDatabase(client["test_movie_mrs"])
    yield db
    # Clean up all collections after each test
    for name in client["test_movie_mrs"].list_collection_names():
        client["test_movie_mrs"][name].drop()


@pytest_asyncio.fixture
async def client(test_db):
    """HTTP client wired to the app with the DB dependency overridden."""

    async def override_get_db(request: Request):
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    # Also patch the app state so lifespan-created indexes don't fail
    app.state.db = test_db

    # Set NLP artifacts to None by default (tests that need them will override)
    app.state.tfidf_vectorizer = None
    app.state.tmdb_ids = []
    app.state.movie_embeddings = None
    app.state.top_indices = None
    app.state.top_scores = None
    # CF artifacts — disabled by default
    app.state.cf_top_indices = None
    app.state.cf_tmdb_ids = []
    app.state.cf_top_scores = None
    app.state.metrics = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_with_hybrid(test_db):
    """HTTP client with NLP + CF artifacts on app.state.

    CF neighbors are set to reverse order relative to NLP neighbors so that
    hybrid blending produces rankings different from pure content-based.
    """
    from app.main import app
    from app.core.database import get_db

    tmdb_ids = list(range(100, 120))
    n = len(tmdb_ids)
    top_indices = np.zeros((n, 50), dtype=np.int32)
    cf_top_indices = np.zeros((n, 50), dtype=np.int32)
    for i in range(n):
        neighbors = [(i + j + 1) % n for j in range(50)]
        top_indices[i] = neighbors
        # CF neighbors: reverse order to create different ranking
        cf_neighbors = [(i + n - j - 1) % n for j in range(50)]
        cf_top_indices[i] = cf_neighbors

    async def override_get_db(request: Request):
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.db = test_db
    app.state.tfidf_vectorizer = None
    app.state.tmdb_ids = tmdb_ids
    app.state.movie_embeddings = None
    app.state.top_indices = top_indices
    app.state.top_scores = None
    app.state.faiss_index = None
    app.state.catalog_cache = {m["tmdb_id"]: m for m in _SEED_MOVIE_DATA}
    app.state.cf_top_indices = cf_top_indices
    app.state.cf_tmdb_ids = tmdb_ids
    app.state.cf_top_scores = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def mock_nlp_state():
    """Create mock NLP artifacts for recommendation tests."""
    # 10 fake movies with tmdb_ids
    tmdb_ids = list(range(100, 110))
    # Each movie's top-50 neighbors (use modular indices for 10 movies)
    top_indices = np.zeros((10, 50), dtype=np.int32)
    for i in range(10):
        neighbors = [(i + j + 1) % 10 for j in range(50)]
        top_indices[i] = neighbors
    return {"tmdb_ids": tmdb_ids, "top_indices": top_indices}


# 20 sample movies covering a range of genres; tmdb_ids 100-119
_SEED_MOVIE_DATA = [
    {"tmdb_id": 100, "title": "Action Hero", "genres": ["Action"], "year": 2020, "rating": 7.5},
    {"tmdb_id": 101, "title": "Action Sequel", "genres": ["Action", "Thriller"], "year": 2021, "rating": 7.2},
    {"tmdb_id": 102, "title": "Rom-Com Classic", "genres": ["Romance", "Comedy"], "year": 2019, "rating": 6.8},
    {"tmdb_id": 103, "title": "Thriller Night", "genres": ["Thriller", "Horror"], "year": 2022, "rating": 7.0},
    {"tmdb_id": 104, "title": "Comedy Nights", "genres": ["Comedy"], "year": 2020, "rating": 6.5},
    {"tmdb_id": 105, "title": "Drama Queens", "genres": ["Drama", "Romance"], "year": 2018, "rating": 7.8},
    {"tmdb_id": 106, "title": "Sci-Fi Future", "genres": ["Science Fiction"], "year": 2023, "rating": 8.0},
    {"tmdb_id": 107, "title": "Horror Mansion", "genres": ["Horror"], "year": 2021, "rating": 6.3},
    {"tmdb_id": 108, "title": "Animated Dreams", "genres": ["Animation", "Comedy"], "year": 2022, "rating": 7.9},
    {"tmdb_id": 109, "title": "Doc Earth", "genres": ["Documentary"], "year": 2020, "rating": 8.2},
    {"tmdb_id": 110, "title": "Action Storm", "genres": ["Action"], "year": 2019, "rating": 7.1},
    {"tmdb_id": 111, "title": "Mystery Mind", "genres": ["Mystery", "Thriller"], "year": 2021, "rating": 7.4},
    {"tmdb_id": 112, "title": "Love Story", "genres": ["Romance"], "year": 2017, "rating": 6.9},
    {"tmdb_id": 113, "title": "Comedy Hour", "genres": ["Comedy", "Animation"], "year": 2023, "rating": 7.0},
    {"tmdb_id": 114, "title": "Dark Drama", "genres": ["Drama"], "year": 2016, "rating": 7.6},
    {"tmdb_id": 115, "title": "Space Odyssey", "genres": ["Science Fiction", "Adventure"], "year": 2024, "rating": 8.1},
    {"tmdb_id": 116, "title": "Nature Doc", "genres": ["Documentary"], "year": 2021, "rating": 8.3},
    {"tmdb_id": 117, "title": "Action Blitz", "genres": ["Action", "Adventure"], "year": 2022, "rating": 7.3},
    {"tmdb_id": 118, "title": "Crime Thriller", "genres": ["Thriller", "Crime"], "year": 2020, "rating": 7.7},
    {"tmdb_id": 119, "title": "Romantic Drama", "genres": ["Romance", "Drama"], "year": 2019, "rating": 7.0},
]


@pytest_asyncio.fixture
async def seed_movies(test_db):
    """Insert 20 sample movie documents into test_db with various genres (tmdb_ids 100-119).

    Uses copies of the data dicts to avoid _id mutation across test runs.
    """
    docs = [dict(m) for m in _SEED_MOVIE_DATA]
    await test_db.movies.insert_many(docs)
    yield docs
    await test_db.movies.delete_many({"tmdb_id": {"$in": [m["tmdb_id"] for m in _SEED_MOVIE_DATA]}})


@pytest_asyncio.fixture
async def client_with_nlp(test_db):
    """HTTP client with DB override AND mock NLP state on app.state.

    tmdb_ids covers all 20 seed movies (100-119).
    top_indices shape (20, 50): each movie's neighbors spread across all others.

    NOTE: does NOT insert seed movies — use the `seed_movies` fixture alongside this
    one when tests require actual movie documents in the database.
    """
    from app.main import app
    from app.core.database import get_db

    # Build realistic NLP state covering 20 seed movies
    tmdb_ids = list(range(100, 120))  # 20 movies
    n = len(tmdb_ids)
    top_indices = np.zeros((n, 50), dtype=np.int32)
    for i in range(n):
        # Neighbors: next 50 indices wrapping around (modular), skipping self
        neighbors = [(i + j + 1) % n for j in range(50)]
        top_indices[i] = neighbors

    async def override_get_db(request: Request):
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    app.state.db = test_db
    app.state.tfidf_vectorizer = None
    app.state.tmdb_ids = tmdb_ids
    app.state.movie_embeddings = None
    app.state.top_indices = top_indices
    app.state.top_scores = None
    app.state.faiss_index = None
    # Populate catalog_cache from seed data so the recommendation service
    # uses genre-aware scoring instead of falling back to top-rated.
    app.state.catalog_cache = {m["tmdb_id"]: m for m in _SEED_MOVIE_DATA}
    # CF artifacts — disabled by default
    app.state.cf_top_indices = None
    app.state.cf_tmdb_ids = []
    app.state.cf_top_scores = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
