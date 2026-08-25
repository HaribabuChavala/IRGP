$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$composeArgs = @(
    '-f', 'docker-compose.yml',
    '-f', 'docker-compose.override.yml',
    '-f', 'docker-compose.microservices.yml'
)

Write-Host 'Stopping full stack with merged compose files...' -ForegroundColor Cyan
& docker compose @composeArgs down --remove-orphans
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Failed to stop full stack cleanly.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nFull stack stopped and cleaned successfully." -ForegroundColor Green
exit 0
