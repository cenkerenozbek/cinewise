"""TMDB response to MongoDB document transform."""

from datetime import datetime, timezone


def transform_movie(tmdb_data: dict) -> dict:
    """Transform TMDB API response into MongoDB movie document."""
    # Director from crew
    credits = tmdb_data.get("credits", {})
    crew = credits.get("crew", [])
    director = next((p["name"] for p in crew if p.get("job") == "Director"), None)

    # Top 5 cast
    cast_list = credits.get("cast", [])
    cast = [p["name"] for p in cast_list[:5]]

    # Turkish title from translations
    translations = tmdb_data.get("translations", {}).get("translations", [])
    title_tr = None
    for t in translations:
        if t.get("iso_639_1") == "tr":
            tr_title = t.get("data", {}).get("title")
            if tr_title:  # Only set if non-empty
                title_tr = tr_title
            break

    # Year from release_date
    release_date = tmdb_data.get("release_date", "") or ""
    year = int(release_date[:4]) if len(release_date) >= 4 else None

    # Genre names
    genres = [g["name"] for g in tmdb_data.get("genres", [])]

    return {
        "tmdb_id": tmdb_data["id"],
        "title": tmdb_data.get("title", "Unknown"),
        "title_tr": title_tr,
        "year": year,
        "genres": genres,
        "overview": tmdb_data.get("overview") or None,
        "poster_path": tmdb_data.get("poster_path"),
        "backdrop_path": tmdb_data.get("backdrop_path"),
        "rating": tmdb_data.get("vote_average"),
        "vote_count": tmdb_data.get("vote_count"),
        "popularity": tmdb_data.get("popularity"),
        "original_language": tmdb_data.get("original_language"),
        "director": director,
        "cast": cast,
        "tagline": tmdb_data.get("tagline") or None,
        "keywords": [kw["name"] for kw in tmdb_data.get("keywords", {}).get("keywords", [])],
        "ingested_at": datetime.now(timezone.utc),
    }
