#!/usr/bin/env bash
# seed.sh — Start MongoDB and run the ingestion worker to populate the database.
# Usage: bash scripts/seed.sh

set -euo pipefail

echo "Starting MongoDB..."
docker-compose up -d mongo

echo "Waiting for MongoDB to be ready..."
sleep 3

echo "Running ingestion worker..."
docker-compose run --rm worker

echo "Seeding complete."
