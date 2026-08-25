#!/usr/bin/env bash
set -euo pipefail

SERVICES=(
  "traefik"
  "keycloak"
  "postgres"
  "opa"
  "redis"
  "vault"
  "api"
  "auth-service"
  "user-management-service"
  "org-registration-service"
  "platform-admin-service"
  "org-portal-service"
  "subscription-service"
  "notification-service"
  "reminder-service"
  "data-source-service"
  "report-generation-service"
  "audit-service"
  "scheduler-service"
  "observability-service"
  "export-service"
  "billing-service"
  "ui"
)

for service in "${SERVICES[@]}"; do
  if docker ps --format '{{.Names}}' | grep -Fxq "$service"; then
    echo "PASS $service is running"
  else
    echo "FAIL $service is not running"
    exit 1
  fi
done

echo "All containers are running."
