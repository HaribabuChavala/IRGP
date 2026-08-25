#!/usr/bin/env bash
set -euo pipefail

URLS=(
  "http://localhost:8088/dashboard/"
  "http://localhost:8081/realms/report-platform"
  "http://report.localhost/health"
  "http://auth.localhost/health"
  "http://users.localhost/health"
  "http://orgs.localhost/health"
  "http://platform-admin.localhost/health"
  "http://portal.localhost/health"
  "http://subscriptions.localhost/health"
  "http://notifications.localhost/health"
  "http://reminders.localhost/health"
  "http://datasources.localhost/health"
  "http://reports.localhost/health"
  "http://audit.localhost/health"
  "http://scheduler.localhost/health"
  "http://observability.localhost/health"
  "http://export.localhost/health"
  "http://billing.localhost/health"
)

echo "Waiting for services to come online..."
ATTEMPTS=30

for ((i=1; i<=ATTEMPTS; i++)); do
  all_ready=true

  for url in "${URLS[@]}"; do
    if ! curl -fsS "$url" >/dev/null 2>&1; then
      all_ready=false
      break
    fi
  done

  if [[ "$all_ready" == true ]]; then
    echo "All configured services are ready."
    exit 0
  fi

  echo "Attempt $i/$ATTEMPTS: waiting for services..."
  sleep 5
done

echo "Timed out waiting for services to become ready." >&2
exit 1
