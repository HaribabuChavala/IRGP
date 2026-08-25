$ErrorActionPreference = 'Stop'

$composeFiles = @(
    'docker-compose.yml',
    'docker-compose.override.yml',
    'docker-compose.microservices.yml'
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Starting base stack ===" -ForegroundColor Cyan
& docker compose up -d --build

Write-Host "`n=== Starting full microservice stack ===" -ForegroundColor Cyan
& docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build

$hostsScript = Join-Path $PSScriptRoot 'ensure-local-hosts.ps1'
Write-Host "`n=== Ensuring localhost aliases ===" -ForegroundColor Cyan
& $hostsScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== Waiting for startup ===" -ForegroundColor Cyan
Start-Sleep -Seconds 20

$checkScript = Join-Path $PSScriptRoot 'Check-Microservices.ps1'
Write-Host "`n=== Verifying health checks ===" -ForegroundColor Cyan
& $checkScript
exit $LASTEXITCODE
