#!/usr/bin/env bash
set -euo pipefail

HOSTS_FILE="/etc/hosts"
ENTRIES=(
  "127.0.0.1 report.localhost"
  "127.0.0.1 app.localhost"
  "127.0.0.1 auth.localhost"
  "127.0.0.1 users.localhost"
  "127.0.0.1 orgs.localhost"
  "127.0.0.1 platform-admin.localhost"
  "127.0.0.1 portal.localhost"
  "127.0.0.1 subscriptions.localhost"
  "127.0.0.1 notifications.localhost"
  "127.0.0.1 reminders.localhost"
  "127.0.0.1 datasources.localhost"
  "127.0.0.1 reports.localhost"
  "127.0.0.1 audit.localhost"
  "127.0.0.1 scheduler.localhost"
  "127.0.0.1 observability.localhost"
  "127.0.0.1 export.localhost"
  "127.0.0.1 billing.localhost"
)

if [[ ! -w "$HOSTS_FILE" ]]; then
  echo "The hosts file is not writable. Run with sudo or as an administrator." >&2
  exit 1
fi

missing=()
for entry in "${ENTRIES[@]}"; do
  if ! grep -qF "$entry" "$HOSTS_FILE"; then
    missing+=("$entry")
  fi
done

if [[ ${#missing[@]} -eq 0 ]]; then
  echo "Localhost aliases already present in hosts file."
  exit 0
fi

{
  echo
  echo "# Added by access-security-lab startup scripts"
  printf '%s\n' "${missing[@]}"
} >> "$HOSTS_FILE"

echo "Added missing localhost aliases to $HOSTS_FILE:"
for entry in "${missing[@]}"; do
  echo "  $entry"
done
