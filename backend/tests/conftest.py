"""
Test configuration and fixtures for the backend API tests.

Uses mongomock for an in-memory MongoDB and overrides the FastAPI app's
get_db dependency so no real MongoDB connection is needed.
"""
import pytest
import pytest_asyncio
import mongomock
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
