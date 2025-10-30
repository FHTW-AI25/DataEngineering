#!/usr/bin/env bash
set -e

CONTAINER_NAME="earthquakes-db"
VOLUME_PATH="../db/volume"

echo "🛑 Stopping database container: ${CONTAINER_NAME} ..."
docker stop "${CONTAINER_NAME}" || true

echo "🗑️ Removing database container ..."
docker rm "${CONTAINER_NAME}" || true

echo "💣 Removing database volume at ${VOLUME_PATH} ..."
rm -rf "${VOLUME_PATH}"
mkdir -p "${VOLUME_PATH}"

echo "🚀 Starting database container again ..."
docker compose up -d db

echo "✅ Database container restarted cleanly."
