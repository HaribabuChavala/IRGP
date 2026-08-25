#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Starting base stack ==="
docker compose up -d --build

echo "=== Starting full microservice stack ==="
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build

echo "=== Ensuring localhost aliases ==="
./scripts/ensure-local-hosts.sh

echo "=== Waiting for services ==="
./scripts/wait-for-services.sh

echo "=== Verifying health checks ==="
./scripts/check-microservices.sh
