"""Incremental Turkish film ingestion + embedding append.

Fetches Turkish-language films from TMDB (vote_count >= MIN_VOTES),
upserts new ones to MongoDB, then appends their embeddings to the
existing similarity_index.joblib WITHOUT recomputing existing films.

Steps:
  1. Discover Turkish films via TMDB /discover/movie (original_language=tr)
  2. Upsert new films to MongoDB (skip already-present tmdb_ids)
  3. Load existing similarity_index.joblib
  4. Embed only the newly ingested films (all-mpnet-base-v2)
  5. Compute similarity rows for new films against all N+M films
  6. Append new rows; existing films keep their neighbour lists untouched
  7. Save updated artifact

Usage:
    python jobs/add_turkish_films.py
    python jobs/add_turkish_films.py --min-votes 10   # looser filter
    python jobs/add_turkish_films.py --dry-run        # fetch + print, no writes
"""

import argparse
import asyncio
import logging
import os
import sys
import time

import httpx
import joblib
import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipelines.fetch_movies import fetch_tmdb, fetch_movie_details
from pipelines.transform import transform_movie
from pipelines.load import upsert_batch
from jobs.nlp_features import preprocess_text, build_semantic_embeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def fetch_turkish_film_ids(
    client: httpx.AsyncClient, min_votes: int
) -> list[int]:
    """Discover all Turkish-language film IDs on TMDB above vote threshold."""
    ids: list[int] = []
    seen: set[int] = set()
    page = 1

    while True:
        data = await fetch_tmdb(
            client,
            "/discover/movie",
            {
                "with_original_language": "tr",
                "sort_by": "popularity.desc",
                "vote_count.gte": min_votes,
                "page": page,
                "language": "en-US",
            },
        )
        results = data.get("results", [])
        if not results:
            break

        for m in results:
            mid = m["id"]
            if mid not in seen:
                seen.add(mid)
                ids.append(mid)

        total_pages = data.get("total_pages", 1)
        logger.info(f"TMDB discover page {page}/{total_pages} — {len(ids)} IDs so far")
        if page >= total_pages:
            break
        page += 1

    return ids


def append_to_artifact(
    artifact_path: str,
    new_tmdb_ids: list[int],
    new_texts: list[str],
    top_n: int = 100,
) -> None:
    """Embed new films and append to existing similarity index."""
    logger.info(f"Loading existing artifact from {artifact_path} ...")
    data = joblib.load(artifact_path)
    old_tmdb_ids: list[int] = data["tmdb_ids"]
    old_embeddings: np.ndarray = data["embeddings"]       # (N, 768)
    old_top_indices: np.ndarray = data["top_indices"]     # (N, 100)
    old_top_scores: np.ndarray = data["top_scores"]       # (N, 100)

    N = len(old_tmdb_ids)
    M = len(new_tmdb_ids)
    logger.info(f"Existing: {N} films — appending {M} new films")

    logger.info("Encoding new films ...")
    new_embeddings = build_semantic_embeddings(new_texts)  # (M, 768), L2-normalised

    # Combined arrays
    all_embeddings = np.vstack([old_embeddings, new_embeddings])  # (N+M, 768)
    all_tmdb_ids = old_tmdb_ids + new_tmdb_ids

    effective_top_n = min(top_n, N + M - 1)

    # Compute similarity rows only for the M new films
    logger.info(f"Computing similarity for {M} new films against all {N + M} ...")
    new_top_indices = np.zeros((M, effective_top_n), dtype=np.int32)
    new_top_scores = np.zeros((M, effective_top_n), dtype=np.float32)

    for i in range(M):
        sims = (all_embeddings @ all_embeddings[N + i]).astype(np.float64)
        sims[N + i] = -2.0  # exclude self
        idx = np.argpartition(sims, -effective_top_n)[-effective_top_n:]
        new_top_indices[i] = idx.astype(np.int32)
        new_top_scores[i] = sims[idx].astype(np.float32)

    # Pad old index arrays if effective_top_n changed (edge case with small catalogs)
    if old_top_indices.shape[1] < effective_top_n:
        pad = effective_top_n - old_top_indices.shape[1]
        old_top_indices = np.pad(old_top_indices, ((0, 0), (0, pad)), constant_values=0)
        old_top_scores = np.pad(old_top_scores, ((0, 0), (0, pad)), constant_values=0.0)
    elif old_top_indices.shape[1] > effective_top_n:
        old_top_indices = old_top_indices[:, :effective_top_n]
        old_top_scores = old_top_scores[:, :effective_top_n]

    all_top_indices = np.vstack([old_top_indices, new_top_indices])
    all_top_scores = np.vstack([old_top_scores, new_top_scores])

    logger.info(f"Saving updated artifact — {N + M} films total ...")
    joblib.dump(
        {
            "tmdb_ids": all_tmdb_ids,
            "embeddings": all_embeddings.astype(np.float32),
            "top_indices": all_top_indices,
            "top_scores": all_top_scores,
        },
        artifact_path,
    )
    logger.info(f"Artifact saved: {artifact_path}")


async def main(min_votes: int, dry_run: bool, force: bool = False) -> None:
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "/artifacts")
    artifact_path = os.path.join(artifacts_dir, "similarity_index.joblib")

    if not tmdb_api_key:
        logger.error("TMDB_API_KEY not set")
        sys.exit(1)

    if not os.path.exists(artifact_path):
        logger.error(f"Artifact not found at {artifact_path}. Run nlp_features.py first.")
        sys.exit(1)

    async with httpx.AsyncClient(
        params={"api_key": tmdb_api_key}, timeout=30.0
    ) as http_client:
        logger.info(f"Discovering Turkish films (vote_count >= {min_votes}) ...")
        all_tr_ids = await fetch_turkish_film_ids(http_client, min_votes)
        logger.info(f"Total Turkish film IDs from TMDB: {len(all_tr_ids)}")

        if dry_run:
            logger.info("[DRY RUN] Would process %d films. Exiting.", len(all_tr_ids))
            return

        from pymongo import AsyncMongoClient
        from shared.config import MOVIES_COLLECTION

        mongo_client = AsyncMongoClient(mongo_uri)
        db = mongo_client[db_name]
        collection = db[MOVIES_COLLECTION]

        # Skip already-ingested films unless --force
        existing = set(
            await collection.distinct("tmdb_id", {"tmdb_id": {"$in": all_tr_ids}})
        )
        new_ids = all_tr_ids if force else [mid for mid in all_tr_ids if mid not in existing]
        logger.info(
            f"Already in DB: {len(existing)} | To ingest: {len(new_ids)}"
            + (" (force update)" if force else "")
        )

        if not new_ids:
            logger.info("No new Turkish films to add.")
            mongo_client.close()
            return

        # Fetch details + upsert
        new_docs = []
        errors = 0
        start = time.time()
        for i, movie_id in enumerate(new_ids, 1):
            try:
                details = await fetch_movie_details(http_client, movie_id)
                new_docs.append(transform_movie(details))
            except Exception as e:
                errors += 1
                logger.warning(f"Failed to fetch {movie_id}: {e}")
            if i % 50 == 0:
                logger.info(f"Fetched {i}/{len(new_ids)} | errors: {errors} | {time.time()-start:.0f}s")

        await upsert_batch(collection, new_docs)
        logger.info(f"Upserted {len(new_docs)} films to MongoDB ({errors} errors)")
        await mongo_client.close()

    if not new_docs:
        logger.info("Nothing to embed.")
        return

    # Only embed films not already in the artifact
    existing_artifact = joblib.load(artifact_path)
    artifact_id_set = set(existing_artifact["tmdb_ids"])
    docs_to_embed = [d for d in new_docs if d["tmdb_id"] not in artifact_id_set]
    logger.info(f"{len(docs_to_embed)} films to embed (skipping {len(new_docs) - len(docs_to_embed)} already in artifact)")

    if not docs_to_embed:
        logger.info("All films already in artifact, skipping embedding step.")
        return

    texts = [
        preprocess_text(
            d.get("overview"),
            d.get("genres", []),
            d.get("cast"),
            d.get("director"),
            d.get("tagline"),
            d.get("keywords"),
        )
        for d in docs_to_embed
    ]
    new_tmdb_ids = [d["tmdb_id"] for d in docs_to_embed]

    append_to_artifact(artifact_path, new_tmdb_ids, texts)
    logger.info(f"Done. Added {len(new_docs)} Turkish films to similarity index.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-votes", type=int, default=50,
                        help="Minimum TMDB vote count (default: 50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and print counts without writing anything")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch and upsert all Turkish films (updates existing records)")
    args = parser.parse_args()
    asyncio.run(main(args.min_votes, args.dry_run, args.force))
