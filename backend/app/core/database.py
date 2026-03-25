from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase


def get_database(request: Request) -> AsyncDatabase:
    """Return the AsyncDatabase instance stored in app state."""
    return request.app.state.db


# FastAPI dependency alias
async def get_db(request: Request) -> AsyncDatabase:
    """FastAPI dependency that yields the async MongoDB database."""
    return request.app.state.db
