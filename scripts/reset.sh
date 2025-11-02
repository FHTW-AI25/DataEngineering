#!/usr/bin/env bash
set -euo pipefail

# Project root = parent of this script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"

DATA_DIR="${PROJECT_ROOT}/data/usgs_earthquakes"
DB_DATA_DIR="${PROJECT_ROOT}/db/volume"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# Pick compose command
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
  COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
else
  echo "docker compose not found" >&2
  exit 1
fi

echo "Stopping and removing containers..."
$COMPOSE -f "${COMPOSE_FILE}" down --remove-orphans || true

# small delay so bind mounts are released
sleep 1

echo "Deleting ${DATA_DIR} ..."
rm -rf -- "${DATA_DIR}"

echo "Deleting ${DB_DATA_DIR} ..."
rm -rf -- "${DB_DATA_DIR}"

echo "Done."
