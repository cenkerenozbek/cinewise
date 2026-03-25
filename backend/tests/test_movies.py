"""
Tests for the movie listing, search, filter, and detail API endpoints.

Covers:
- GET /api/movies                (list, pagination)
- GET /api/movies?q=...          (title search)
- GET /api/movies?genre=...      (genre filter)
- GET /api/movies?year=...       (year filter)
- GET /api/movies?q=...&genre=...&year=...  (combined filters)
- GET /api/movies/{tmdb_id}      (movie detail)
- GET /api/movies/999999         (not found 404)
- GET /api/movies/genres         (distinct genre list)
- Performance: search responds within 2 seconds (API-06)
"""
import time

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Sample movie documents used as test data
# ---------------------------------------------------------------------------

def _make_movie(tmdb_id, title, year, genres, popularity=5.0, rating=7.0, **kwargs):
    """Helper to build a minimal movie document."""
    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "title_tr": kwargs.get("title_tr"),
        "year": year,
        "genres": genres,
        "overview": kwargs.get("overview", f"Overview of {title}"),
        "poster_path": kwargs.get("poster_path", f"/poster_{tmdb_id}.jpg"),
        "rating": rating,
        "vote_count": kwargs.get("vote_count", 1000),
        "popularity": popularity,
        "director": kwargs.get("director", "Test Director"),
        "cast": kwargs.get("cast", ["Actor One", "Actor Two"]),
    }


SAMPLE_MOVIES = [
    _make_movie(27205, "Inception", 2010, ["Action", "Sci-Fi"], popularity=100.0),
    _make_movie(
        468589,
        "The Dark Knight",
        2008,
        ["Action", "Crime", "Drama"],
        popularity=90.0,
        title_tr="Kara Şövalye",
    ),
    _make_movie(299534, "Avengers: Endgame", 2019, ["Action", "Adventure"], popularity=80.0),
    _make_movie(19404, "Dilwale Dulhania Le Jayenge", 1995, ["Drama", "Romance"], popularity=50.0),
    _make_movie(550, "Fight Club", 1999, ["Drama", "Thriller"], popularity=60.0),
    _make_movie(13, "Forrest Gump", 1994, ["Drama", "Romance"], popularity=55.0),
    _make_movie(120, "The Lord of the Rings: The Fellowship of the Ring", 2001, ["Adventure", "Fantasy"], popularity=70.0),
    _make_movie(155, "The Dark Knight Rises", 2012, ["Action", "Crime"], popularity=85.0),
    _make_movie(238, "The Godfather", 1972, ["Crime", "Drama"], popularity=65.0),
    _make_movie(278, "The Shawshank Redemption", 1994, ["Drama"], popularity=75.0),
]

# Generate 90 extra movies with "dark" in the title for the performance test
EXTRA_MOVIES = [
    _make_movie(
        90000 + i,
        f"Dark Movie {i}",
        2000 + (i % 25),
        ["Action"] if i % 2 == 0 else ["Drama"],
        popularity=float(i),
    )
    for i in range(90)
]

ALL_MOVIES = SAMPLE_MOVIES + EXTRA_MOVIES  # 100 movies total


@pytest.fixture
async def seeded_db(test_db):
    """Insert SAMPLE_MOVIES into the test database."""
    for movie in SAMPLE_MOVIES:
        await test_db["movies"].insert_one(dict(movie))
    yield test_db
    await test_db["movies"].delete_many({})


@pytest.fixture
async def seeded_movies_100(test_db):
    """Insert 100 movies (including many with 'dark') for performance test."""
    for movie in ALL_MOVIES:
        await test_db["movies"].insert_one(dict(movie))
    yield test_db
    await test_db["movies"].delete_many({})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_list_movies(client: AsyncClient, seeded_db):
    """Test 1: GET /api/movies returns paginated response envelope."""
    response = await client.get("/api/movies")
    assert response.status_code == 200
    data = response.json()
    assert "movies" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["movies"], list)
    assert data["page"] == 1


async def test_search_by_title(client: AsyncClient, seeded_db):
    """Test 2: GET /api/movies?q=inception returns matching movies (case-insensitive)."""
    response = await client.get("/api/movies", params={"q": "inception"})
    assert response.status_code == 200
    data = response.json()
    titles = [m["title"].lower() for m in data["movies"]]
    assert any("inception" in t for t in titles), f"No matching title in {titles}"


async def test_filter_by_genre(client: AsyncClient, seeded_db):
    """Test 3: GET /api/movies?genre=Action returns only Action movies."""
    response = await client.get("/api/movies", params={"genre": "Action"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["movies"]) > 0
    for movie in data["movies"]:
        assert "Action" in movie["genres"], f"Expected 'Action' in {movie['genres']}"


async def test_filter_by_year(client: AsyncClient, seeded_db):
    """Test 4: GET /api/movies?year=2010 returns only 2010 movies."""
    response = await client.get("/api/movies", params={"year": 2010})
    assert response.status_code == 200
    data = response.json()
    assert len(data["movies"]) > 0
    for movie in data["movies"]:
        assert movie["year"] == 2010, f"Expected year 2010, got {movie['year']}"


async def test_combined_filters(client: AsyncClient, seeded_db):
    """Test 5: GET /api/movies?q=dark&genre=Action&year=2008 returns filtered results."""
    response = await client.get(
        "/api/movies", params={"q": "dark", "genre": "Action", "year": 2008}
    )
    assert response.status_code == 200
    data = response.json()
    # Should return The Dark Knight (2008, Action) or empty — no crash
    for movie in data["movies"]:
        assert "Action" in movie["genres"]
        assert movie["year"] == 2008


async def test_movie_detail(client: AsyncClient, seeded_db):
    """Test 6: GET /api/movies/{tmdb_id} returns full movie document."""
    response = await client.get("/api/movies/27205")  # Inception
    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_id"] == 27205
    assert data["title"] == "Inception"
    # MovieDetail fields
    assert "overview" in data
    assert "cast" in data
    assert "director" in data


async def test_movie_not_found(client: AsyncClient, seeded_db):
    """Test 7: GET /api/movies/999999 returns 404."""
    response = await client.get("/api/movies/999999")
    assert response.status_code == 404


async def test_pagination(client: AsyncClient, seeded_db):
    """Test 8: GET /api/movies?page=2&page_size=3 returns correct page."""
    # First, get all movies (page 1) with page_size=3
    r1 = await client.get("/api/movies", params={"page": 1, "page_size": 3})
    r2 = await client.get("/api/movies", params={"page": 2, "page_size": 3})

    assert r1.status_code == 200
    assert r2.status_code == 200

    page1_titles = [m["title"] for m in r1.json()["movies"]]
    page2_titles = [m["title"] for m in r2.json()["movies"]]

    # Pages should not overlap
    assert not set(page1_titles).intersection(page2_titles)


async def test_genres_list(client: AsyncClient, seeded_db):
    """Test 9: GET /api/movies/genres returns list of distinct genre strings."""
    response = await client.get("/api/movies/genres")
    assert response.status_code == 200
    data = response.json()
    assert "genres" in data
    genres = data["genres"]
    assert isinstance(genres, list)
    assert len(genres) > 0
    # Should include genres from seed data
    assert "Action" in genres
    assert "Drama" in genres
    # Should be sorted alphabetically
    assert genres == sorted(genres)


async def test_search_performance(client: AsyncClient, seeded_movies_100):
    """Test 10: API-06 — Search API responds within 2 seconds (p95)."""
    start = time.perf_counter()
    response = await client.get("/api/movies", params={"q": "dark"})
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 2.0, f"Search took {elapsed:.2f}s, exceeds 2s p95 target"
