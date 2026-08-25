#!/usr/bin/env bash
set -euo pipefail

URLS=(
  "http://localhost:8088/dashboard/"
  "http://localhost:8081/realms/report-platform"
  "http://report.localhost/health"
  "http://app.localhost"
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

failures=0

for url in "${URLS[@]}"; do
  if curl -fsS "$url" >/dev/null 2>&1; then
    echo "PASS $url"
  else
    echo "FAIL $url"
    failures=$((failures+1))
  fi
done

if (( failures > 0 )); then
  echo "Health check failed for $failures endpoint(s)." >&2
  exit 1
fi

echo "All configured services are responding."
