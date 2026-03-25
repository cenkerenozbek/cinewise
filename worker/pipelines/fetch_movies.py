"""TMDB API fetching with pagination and retry/backoff."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)
TMDB_BASE = "https://api.themoviedb.org/3"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    before_sleep=lambda retry_state: logger.warning(
        f"TMDB API retry attempt {retry_state.attempt_number}"
    ),
)
async def fetch_tmdb(client: httpx.AsyncClient, path: str, params: dict = None) -> dict:
    """Fetch a TMDB API endpoint with retry/backoff on failures."""
    resp = await client.get(f"{TMDB_BASE}{path}", params=params or {})
    resp.raise_for_status()
    return resp.json()


async def fetch_movie_ids(client: httpx.AsyncClient, target_count: int = 5000) -> list[int]:
    """Fetch movie IDs from popular and top_rated endpoints until target_count reached."""
    seen_ids = []
    seen_set = set()
    for endpoint in ["/movie/popular", "/movie/top_rated"]:
        page = 1
        while len(seen_ids) < target_count:
            data = await fetch_tmdb(client, endpoint, {"page": page, "language": "en-US"})
            results = data.get("results", [])
            if not results:
                break
            for movie in results:
                mid = movie["id"]
                if mid not in seen_set:
                    seen_set.add(mid)
                    seen_ids.append(mid)
            total_pages = data.get("total_pages", 1)
            if page >= total_pages or page >= 500:
                break
            page += 1
        if len(seen_ids) >= target_count:
            break
    return seen_ids[:target_count]


async def fetch_movie_details(client: httpx.AsyncClient, movie_id: int) -> dict:
    """Fetch movie details with credits and translations in one call."""
    return await fetch_tmdb(
        client,
        f"/movie/{movie_id}",
        {"append_to_response": "credits,translations", "language": "en-US"},
    )
