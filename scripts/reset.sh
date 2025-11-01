#!/usr/bin/env bash
set -euo pipefail

echo "Stopping and removing containers..."
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
  docker compose down --remove-orphans || true
elif command -v docker-compose &>/dev/null; then
  docker-compose down --remove-orphans || true
else
  echo "docker compose not found" >&2
  exit 1
fi

echo "Deleting data/usgs_earthquakes..."
rm -rf ../data/usgs_earthquakes

echo "Deleting db/volume..."
rm -rf ../db/volume

echo "Done."
