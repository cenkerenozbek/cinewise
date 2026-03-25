"""Pipeline unit tests for fetch, transform, and load modules."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime


# ---------------------------------------------------------------------------
# Transform tests (Tests 1-7)
# ---------------------------------------------------------------------------

class TestTransformMovie:
    def test_transform_movie(self, sample_tmdb_response):
        """Test 1: transform_movie with complete response returns all required fields."""
        from pipelines.transform import transform_movie

        result = transform_movie(sample_tmdb_response)

        assert result["tmdb_id"] == 550
        assert result["title"] == "Fight Club"
        assert result["title_tr"] == "Dövüş Kulübü"
        assert result["year"] == 1999
        assert result["genres"] == ["Drama", "Thriller"]
        assert result["overview"] == "A ticking-time-bomb insomniac and a slippery soap salesman..."
        assert result["poster_path"] == "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert result["rating"] == 8.4
        assert result["vote_count"] == 24000
        assert result["popularity"] == 62.5
        assert result["director"] == "David Fincher"
        assert result["cast"] == ["Brad Pitt", "Edward Norton", "Helena Bonham Carter", "Meat Loaf", "Jared Leto"]
        assert isinstance(result["ingested_at"], datetime)

    def test_transform_missing_fields(self, sample_tmdb_response_minimal):
        """Test 2: transform_movie with null/empty fields returns without crashing."""
        from pipelines.transform import transform_movie

        result = transform_movie(sample_tmdb_response_minimal)

        assert result["tmdb_id"] == 999
        assert result["overview"] is None
        assert result["poster_path"] is None
        assert result["cast"] == []
        assert result["director"] is None
        assert result["title_tr"] is None
        assert result["year"] is None
        assert result["genres"] == []

    def test_transform_turkish_title(self, sample_tmdb_response):
        """Test 3: transform_movie extracts title_tr from translations with iso_639_1='tr'."""
        from pipelines.transform import transform_movie

        result = transform_movie(sample_tmdb_response)

        assert result["title_tr"] == "Dövüş Kulübü"

    def test_transform_no_turkish_title(self):
        """Test 4: transform_movie with no Turkish translation sets title_tr=None."""
        from pipelines.transform import transform_movie

        data = {
            "id": 1,
            "title": "Some Movie",
            "overview": "Test",
            "poster_path": None,
            "release_date": "2020-01-01",
            "vote_average": 7.0,
            "vote_count": 100,
            "popularity": 10.0,
            "genres": [],
            "credits": {"crew": [], "cast": []},
            "translations": {
                "translations": [
                    {
                        "iso_639_1": "fr",
                        "iso_3166_1": "FR",
                        "data": {"title": "Un Film", "overview": ""},
                    }
                ]
            },
        }

        result = transform_movie(data)
        assert result["title_tr"] is None

    def test_transform_director(self, sample_tmdb_response):
        """Test 5: transform_movie extracts director from credits.crew where job=='Director'."""
        from pipelines.transform import transform_movie

        result = transform_movie(sample_tmdb_response)
        assert result["director"] == "David Fincher"

    def test_transform_cast_top5(self, sample_tmdb_response):
        """Test 6: transform_movie extracts only first 5 cast names."""
        from pipelines.transform import transform_movie

        result = transform_movie(sample_tmdb_response)
        assert len(result["cast"]) == 5
        assert result["cast"] == [
            "Brad Pitt", "Edward Norton", "Helena Bonham Carter", "Meat Loaf", "Jared Leto"
        ]
        assert "Zach Grenier" not in result["cast"]

    def test_transform_year_extraction(self):
        """Test 7: transform_movie extracts year from release_date; empty date yields None."""
        from pipelines.transform import transform_movie

        # With valid release_date
        data_with_date = {
            "id": 1,
            "title": "Test",
            "overview": None,
            "poster_path": None,
            "release_date": "2010-07-16",
            "vote_average": None,
            "vote_count": None,
            "popularity": None,
            "genres": [],
            "credits": {"crew": [], "cast": []},
            "translations": {"translations": []},
        }
        result = transform_movie(data_with_date)
        assert result["year"] == 2010

        # With empty release_date
        data_no_date = dict(data_with_date)
        data_no_date["release_date"] = ""
        result_no_date = transform_movie(data_no_date)
        assert result_no_date["year"] is None


# ---------------------------------------------------------------------------
# Fetch tests (Test 8)
# ---------------------------------------------------------------------------

class TestFetchRetry:
    @pytest.mark.asyncio
    async def test_fetch_retry_on_429(self, mock_httpx_client_factory):
        """Test 8: fetch_tmdb retries on 429 HTTPStatusError up to 5 times."""
        from pipelines.fetch_movies import fetch_tmdb

        MockResponse = mock_httpx_client_factory

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MockResponse(429)
            return MockResponse(200, {"results": [], "total_pages": 1})

        mock_client = MagicMock()
        mock_client.get = mock_get

        # Patch tenacity to not actually sleep between retries in tests
        with patch("tenacity.nap.sleep"):
            result = await fetch_tmdb(mock_client, "/movie/popular", {"page": 1})

        assert result == {"results": [], "total_pages": 1}
        assert call_count == 3  # Failed twice, succeeded on third attempt


# ---------------------------------------------------------------------------
# Upsert tests (Tests 9-10)
# ---------------------------------------------------------------------------

class TestUpsertMovie:
    @pytest.mark.asyncio
    async def test_upsert_creates_new(self):
        """Test 9: upsert_movie inserts new document when tmdb_id not present."""
        from pipelines.load import upsert_movie

        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()

        movie_doc = {
            "tmdb_id": 550,
            "title": "Fight Club",
            "ingested_at": datetime.utcnow(),
        }

        await upsert_movie(mock_collection, movie_doc)

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        # First positional arg is the filter
        assert call_args[0][0] == {"tmdb_id": 550}
        # Second positional arg is the update
        assert "$set" in call_args[0][1]
        # upsert=True keyword arg
        assert call_args[1]["upsert"] is True

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self):
        """Test 10: upsert_movie updates existing document with same tmdb_id (no duplicate)."""
        from pipelines.load import upsert_movie

        call_log = []
        filter_used = {}

        async def fake_update_one(filter_doc, update_doc, upsert=False):
            call_log.append((filter_doc, update_doc, upsert))
            return MagicMock(matched_count=1, upserted_id=None)

        mock_collection = MagicMock()
        mock_collection.update_one = fake_update_one

        movie_doc_v1 = {"tmdb_id": 550, "title": "Fight Club", "rating": 8.0}
        movie_doc_v2 = {"tmdb_id": 550, "title": "Fight Club", "rating": 8.5}

        await upsert_movie(mock_collection, movie_doc_v1)
        await upsert_movie(mock_collection, movie_doc_v2)

        # Both calls used the same tmdb_id filter (upsert semantics)
        assert len(call_log) == 2
        assert call_log[0][0] == {"tmdb_id": 550}
        assert call_log[1][0] == {"tmdb_id": 550}
        assert call_log[0][2] is True  # upsert=True
        assert call_log[1][2] is True  # upsert=True
