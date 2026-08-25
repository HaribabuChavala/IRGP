#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy .env.production.example and set real values." >&2
  exit 1
fi

required=(
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_DB
  KEYCLOAK_ADMIN_USERNAME
  KEYCLOAK_ADMIN_PASSWORD
  KEYCLOAK_DB_USER
  KEYCLOAK_DB_PASSWORD
  VAULT_TOKEN
  VAULT_ADDR
  DATABASE_URL
  KEYCLOAK_ISSUER
  KEYCLOAK_JWKS_URL
  NEXT_PUBLIC_API_BASE_URL
  NEXT_PUBLIC_KEYCLOAK_URL
  GOOGLE_ADK_AGENT_URL
)

insecure_patterns=(
  change-me
  replace-with
  dev-root-token
  postgres-dev-password
  keycloak-dev-password
  local-adk-test-key
)

declare -A vals
while IFS='=' read -r k v; do
  [[ -z "${k// }" ]] && continue
  [[ "$k" =~ ^[[:space:]]*# ]] && continue
  vals["$(echo "$k" | xargs)"]="$(echo "$v" | sed 's/^ *//;s/ *$//')"
done < "$ENV_FILE"

missing=()
for key in "${required[@]}"; do
  if [[ -z "${vals[$key]:-}" ]]; then
    missing+=("$key")
  fi
done

insecure=()
for key in "${!vals[@]}"; do
  value="${vals[$key],,}"
  for p in "${insecure_patterns[@]}"; do
    if [[ "$value" == *"$p"* ]]; then
      insecure+=("$key=${vals[$key]}")
      break
    fi
  done
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing required variables:"
  for m in "${missing[@]}"; do echo " - $m"; done
fi

if (( ${#insecure[@]} > 0 )); then
  echo "Insecure placeholder values found:"
  for i in "${insecure[@]}"; do echo " - $i"; done
fi

if (( ${#missing[@]} == 0 && ${#insecure[@]} == 0 )); then
  echo "Production preflight passed for $ENV_FILE"
  exit 0
fi

exit 1
