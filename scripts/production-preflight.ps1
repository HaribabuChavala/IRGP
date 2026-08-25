param(
  [string]$EnvFile = ".env.production"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
  Write-Error "Missing $EnvFile. Copy .env.production.example and set real values."
}

$required = @(
  "POSTGRES_USER",
  "POSTGRES_PASSWORD",
  "POSTGRES_DB",
  "KEYCLOAK_ADMIN_USERNAME",
  "KEYCLOAK_ADMIN_PASSWORD",
  "KEYCLOAK_DB_USER",
  "KEYCLOAK_DB_PASSWORD",
  "VAULT_TOKEN",
  "VAULT_ADDR",
  "DATABASE_URL",
  "KEYCLOAK_ISSUER",
  "KEYCLOAK_JWKS_URL",
  "NEXT_PUBLIC_API_BASE_URL",
  "NEXT_PUBLIC_KEYCLOAK_URL",
  "GOOGLE_ADK_AGENT_URL"
)

$insecurePatterns = @(
  "change-me",
  "replace-with",
  "dev-root-token",
  "postgres-dev-password",
  "keycloak-dev-password",
  "local-adk-test-key"
)

$lines = Get-Content $EnvFile
$map = @{}
foreach ($line in $lines) {
  if ($line -match "^\s*#" -or $line -notmatch "=") { continue }
  $parts = $line.Split("=", 2)
  $k = $parts[0].Trim()
  $v = $parts[1].Trim()
  $map[$k] = $v
}

$missing = @()
foreach ($k in $required) {
  if (-not $map.ContainsKey($k) -or [string]::IsNullOrWhiteSpace($map[$k])) {
    $missing += $k
  }
}

$insecure = @()
foreach ($entry in $map.GetEnumerator()) {
  foreach ($pattern in $insecurePatterns) {
    if ($entry.Value.ToLower().Contains($pattern)) {
      $insecure += "$($entry.Key)=$($entry.Value)"
      break
    }
  }
}

if ($missing.Count -gt 0) {
  Write-Host "Missing required variables:" -ForegroundColor Yellow
  $missing | ForEach-Object { Write-Host " - $_" }
}

if ($insecure.Count -gt 0) {
  Write-Host "Insecure placeholder values found:" -ForegroundColor Yellow
  $insecure | ForEach-Object { Write-Host " - $_" }
}

if ($missing.Count -eq 0 -and $insecure.Count -eq 0) {
  Write-Host "Production preflight passed for $EnvFile" -ForegroundColor Green
  exit 0
}

exit 1
