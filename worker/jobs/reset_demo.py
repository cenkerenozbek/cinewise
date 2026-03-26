"""Demo state reset script for capstone presentations and UAT sessions.

Creates (if needed) and resets two demo accounts:
  - demo_returning (demo_returning@mrs.test): 5+ canonical likes for CF-blended recs
  - demo_coldstart (demo_coldstart@mrs.test): fresh account with zero interactions

Also deletes UAT test accounts matching a configurable email prefix.

Usage:
    python jobs/reset_demo.py [--uat-prefix uat_] [--dry-run]

Environment variables:
    MONGO_URI    MongoDB connection string (default: mongodb://localhost:27017)
    DB_NAME      Database name (default: movie_mrs)
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

# Add project root to path so shared/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEMO_RETURNING_EMAIL = "demo_returning@mrs.test"
DEMO_RETURNING_PASSWORD = "DemoPass123!"
DEMO_COLDSTART_EMAIL = "demo_coldstart@mrs.test"
DEMO_COLDSTART_PASSWORD = "DemoPass123!"
DEFAULT_UAT_PREFIX = "uat_"

# Canonical likes for demo_returning — popular movies likely in any TMDB-seeded DB.
# TMDB IDs: The Shawshank Redemption (278), The Dark Knight (155),
# Inception (27205), Forrest Gump (13), The Matrix (603), Pulp Fiction (680)
CANONICAL_LIKE_TMDB_IDS = [278, 155, 27205, 13, 603, 680]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def ensure_user_exists(db, email: str, password: str) -> str:
    """Return the user_id for the given email, creating the account if absent.

    Args:
        db: Async MongoDB database handle.
        email: Email address of the demo account.
        password: Plain-text password to hash if the account must be created.

    Returns:
        String representation of the user's MongoDB _id.
    """
    user = await db.users.find_one({"email": email})
    if user:
        logger.info(f"Found existing account: {email} (id={user['_id']})")
        return str(user["_id"])

    # Hash password using passlib bcrypt (compatible with backend auth)
    from passlib.hash import bcrypt as passlib_bcrypt  # noqa: PLC0415

    hashed = passlib_bcrypt.hash(password)
    result = await db.users.insert_one({"email": email, "hashed_password": hashed})
    user_id = str(result.inserted_id)
    logger.info(f"Created new account: {email} (id={user_id})")
    return user_id


async def reset_demo(db, dry_run: bool = False) -> None:
    """Reset demo_returning and demo_coldstart accounts to a clean, presentable state.

    For demo_returning: clears all interactions then re-seeds canonical likes so
    CF-blended recommendations work consistently. For demo_coldstart: clears all
    interactions so it represents a genuine first-visit cold-start scenario.

    Args:
        db: Async MongoDB database handle.
        dry_run: If True, log actions without writing to the database.
    """
    if dry_run:
        logger.info("[DRY RUN] Would ensure demo_returning account exists and reset interactions")
        logger.info("[DRY RUN] Would ensure demo_coldstart account exists and clear interactions")
        logger.info(f"[DRY RUN] Would re-seed {len(CANONICAL_LIKE_TMDB_IDS)} canonical likes for demo_returning")
        return

    # Ensure both accounts exist
    returning_user_id = await ensure_user_exists(db, DEMO_RETURNING_EMAIL, DEMO_RETURNING_PASSWORD)
    coldstart_user_id = await ensure_user_exists(db, DEMO_COLDSTART_EMAIL, DEMO_COLDSTART_PASSWORD)

    # Clear all existing interactions for both accounts
    result_r = await db.interactions.delete_many({"user_id": returning_user_id})
    logger.info(f"Deleted {result_r.deleted_count} existing interactions for demo_returning")

    result_c = await db.interactions.delete_many({"user_id": coldstart_user_id})
    logger.info(f"Deleted {result_c.deleted_count} existing interactions for demo_coldstart")

    # Determine which canonical TMDB IDs exist in our movies collection
    existing = await db.movies.find(
        {"tmdb_id": {"$in": CANONICAL_LIKE_TMDB_IDS}},
        {"tmdb_id": 1},
    ).to_list(length=None)
    valid_tmdb_ids = [d["tmdb_id"] for d in existing]
    logger.info(f"Found {len(valid_tmdb_ids)} of {len(CANONICAL_LIKE_TMDB_IDS)} canonical movies in DB")

    # Fallback: use top-6 highest-rated movies if too few canonical IDs are present
    if len(valid_tmdb_ids) < 5:
        logger.warning(
            "Fewer than 5 canonical movies found in DB — falling back to top-6 rated movies"
        )
        fallback = await db.movies.find(
            {"rating": {"$ne": None}}, {"tmdb_id": 1}
        ).sort("rating", -1).limit(6).to_list(length=None)
        valid_tmdb_ids = [d["tmdb_id"] for d in fallback]
        logger.info(f"Fallback: using {len(valid_tmdb_ids)} top-rated movies")

    # Re-seed canonical likes for demo_returning via upsert
    for tmdb_id in valid_tmdb_ids:
        await db.interactions.update_one(
            {"user_id": returning_user_id, "movie_id": tmdb_id},
            {
                "$set": {
                    "user_id": returning_user_id,
                    "movie_id": tmdb_id,
                    "action": "like",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    logger.info(
        f"Re-seeded {len(valid_tmdb_ids)} canonical likes for demo_returning ({DEMO_RETURNING_EMAIL})"
    )
    logger.info(f"demo_coldstart ({DEMO_COLDSTART_EMAIL}) cleared — ready for cold-start demo")


async def cleanup_uat_accounts(db, uat_prefix: str, dry_run: bool = False) -> None:
    """Delete UAT test accounts and all their associated data.

    Finds all user accounts whose email starts with uat_prefix, then removes
    their interactions, preferences, and user documents.

    Args:
        db: Async MongoDB database handle.
        uat_prefix: Email prefix identifying UAT accounts (e.g. "uat_").
        dry_run: If True, log actions without writing to the database.
    """
    uat_users = await db.users.find(
        {"email": {"$regex": f"^{uat_prefix}"}}
    ).to_list(length=None)

    if not uat_users:
        logger.info(f"No UAT accounts found with prefix '{uat_prefix}'")
        return

    uat_ids = [str(u["_id"]) for u in uat_users]
    uat_emails = [u["email"] for u in uat_users]

    logger.info(f"Found {len(uat_users)} UAT accounts: {uat_emails}")

    if dry_run:
        logger.info(f"[DRY RUN] Would delete {len(uat_users)} UAT accounts and all related data")
        return

    # Delete interactions
    del_interactions = await db.interactions.delete_many({"user_id": {"$in": uat_ids}})

    # Delete preferences
    del_prefs = await db.user_preferences.delete_many({"user_id": {"$in": uat_ids}})

    # Delete user accounts
    del_users = await db.users.delete_many({"email": {"$regex": f"^{uat_prefix}"}})

    logger.info(
        f"Cleaned up UAT accounts: {del_users.deleted_count} users, "
        f"{del_interactions.deleted_count} interactions, "
        f"{del_prefs.deleted_count} preferences deleted"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Orchestrate demo reset: ensure accounts, reset interactions, clean UAT data."""
    parser = argparse.ArgumentParser(
        description="Reset demo accounts and clean up UAT test data"
    )
    parser.add_argument(
        "--uat-prefix",
        type=str,
        default=DEFAULT_UAT_PREFIX,
        help=f"Email prefix for UAT accounts to delete (default: '{DEFAULT_UAT_PREFIX}')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to the database",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "movie_mrs")

    logger.info(f"Connecting to MongoDB at {mongo_uri}, db={db_name}")
    client = AsyncMongoClient(mongo_uri)
    db = client[db_name]

    await reset_demo(db, dry_run=args.dry_run)
    await cleanup_uat_accounts(db, args.uat_prefix, dry_run=args.dry_run)

    print("\nDemo state reset complete. Ready for presentation.")
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
