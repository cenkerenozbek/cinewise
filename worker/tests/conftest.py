"""Shared test fixtures for worker pipeline tests."""

import pytest
import httpx


@pytest.fixture
def sample_tmdb_response():
    """Complete TMDB movie detail response dict (with credits, translations including Turkish)."""
    return {
        "id": 550,
        "title": "Fight Club",
        "overview": "A ticking-time-bomb insomniac and a slippery soap salesman...",
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "release_date": "1999-10-15",
        "vote_average": 8.4,
        "vote_count": 24000,
        "popularity": 62.5,
        "genres": [
            {"id": 18, "name": "Drama"},
            {"id": 53, "name": "Thriller"},
        ],
        "credits": {
            "crew": [
                {"name": "David Fincher", "job": "Director", "department": "Directing"},
                {"name": "Jim Uhls", "job": "Screenplay", "department": "Writing"},
            ],
            "cast": [
                {"name": "Brad Pitt", "order": 0},
                {"name": "Edward Norton", "order": 1},
                {"name": "Helena Bonham Carter", "order": 2},
                {"name": "Meat Loaf", "order": 3},
                {"name": "Jared Leto", "order": 4},
                {"name": "Zach Grenier", "order": 5},
            ],
        },
        "translations": {
            "translations": [
                {
                    "iso_639_1": "tr",
                    "iso_3166_1": "TR",
                    "name": "Türkçe",
                    "data": {"title": "Dövüş Kulübü", "overview": ""},
                },
                {
                    "iso_639_1": "fr",
                    "iso_3166_1": "FR",
                    "name": "Français",
                    "data": {"title": "Fight Club", "overview": ""},
                },
            ]
        },
    }


@pytest.fixture
def sample_tmdb_response_minimal():
    """TMDB response with null overview, null poster_path, empty credits, no translations."""
    return {
        "id": 999,
        "title": "Unknown Movie",
        "overview": None,
        "poster_path": None,
        "release_date": "",
        "vote_average": None,
        "vote_count": None,
        "popularity": None,
        "genres": [],
        "credits": {
            "crew": [],
            "cast": [],
        },
        "translations": {
            "translations": []
        },
    }


@pytest.fixture
def mock_httpx_client_factory():
    """Factory for creating mock httpx clients that simulate API responses."""
    class MockResponse:
        def __init__(self, status_code, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", "https://api.themoviedb.org/3/test")
                raise httpx.HTTPStatusError(
                    f"HTTP {self.status_code}",
                    request=request,
                    response=httpx.Response(self.status_code, request=request),
                )

        def json(self):
            return self._json_data

    return MockResponse
