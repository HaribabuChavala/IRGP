#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Seeding demo data into PostgreSQL..."
docker exec -i access-postgres psql -U admin -d report_platform < postgres/seed/demo-data.sql

echo "Demo data seeded successfully."
