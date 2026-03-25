"""
Shared MongoDB document schemas for backend and worker.

These schema dictionaries document the expected structure of documents
stored in MongoDB collections. They serve as a reference/contract — actual
validation uses Pydantic models in the backend.
"""

from datetime import datetime
from typing import Optional

movie_schema = {
    "tmdb_id": int,                   # TMDB movie ID — unique key for upsert
    "title": str,                     # Original English title
    "title_tr": "Optional[str]",      # Turkish title from translations endpoint
    "year": "Optional[int]",          # Release year extracted from release_date
    "genres": "list[str]",            # Genre name strings (not TMDB IDs)
    "overview": "Optional[str]",      # Plot summary
    "poster_path": "Optional[str]",   # TMDB poster path (prepend base URL to use)
    "rating": "Optional[float]",      # vote_average from TMDB
    "vote_count": "Optional[int]",    # Number of votes
    "popularity": "Optional[float]",  # TMDB popularity score
    "director": "Optional[str]",      # From credits crew where job == "Director"
    "cast": "list[str]",              # Top 5 cast member names
    "ingested_at": "datetime",        # UTC timestamp of last ingestion
}

user_schema = {
    "email": str,                     # Unique — used as login identifier
    "hashed_password": str,           # bcrypt hash via passlib
    "display_name": "Optional[str]",  # Optional — derived from email if absent
    "created_at": "datetime",         # UTC timestamp of registration
}
