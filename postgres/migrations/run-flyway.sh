#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="flyway/flyway:11.0.0"

# Adjust as needed for your local database host.
# For local Docker Desktop, localhost is the correct host from the workstation.

docker run --rm \
  -v "${DIR}/flyway:/flyway/conf" \
  -v "${DIR}/flyway/sql:/flyway/sql" \
  --network host \
  "$IMAGE" \
  -configFiles=/flyway/conf/flyway.conf migrate
