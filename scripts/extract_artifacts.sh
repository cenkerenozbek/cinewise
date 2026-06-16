#!/bin/bash
# Run this AFTER Docker Desktop starts.
# Extracts ML artifacts from Docker volume into backend/artifacts/

set -e

VOLUME="cinewise-main_nlp_artifacts"
DEST="$(dirname "$0")/../backend/artifacts"

echo "Checking volume: $VOLUME"

# List what's in the volume
docker run --rm -v "$VOLUME":/artifacts alpine ls -lh /artifacts

echo ""
echo "Extracting artifacts to $DEST ..."

docker run --rm \
  -v "$VOLUME":/artifacts \
  -v "$(cd "$DEST" && pwd)":/output \
  alpine sh -c "cp /artifacts/*.joblib /output/ 2>/dev/null; cp /artifacts/*.json /output/ 2>/dev/null; echo 'Done.'"

echo ""
echo "Files in backend/artifacts/:"
ls -lh "$(dirname "$0")/../backend/artifacts/"
