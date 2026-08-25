#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="liquibase/liquibase:4.25.1"

docker run --rm \
  -v "${DIR}/liquibase:/liquibase/changelog" \
  --network host \
  "$IMAGE" \
  --defaultsFile=/liquibase/changelog/liquibase.properties update
