param(
    [switch]$SkipBuild,
    [switch]$Verify
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$composeArgs = @(
    '-f', 'docker-compose.yml',
    '-f', 'docker-compose.override.yml',
    '-f', 'docker-compose.microservices.yml'
)

Write-Host 'Stopping compose stack...' -ForegroundColor Cyan
try {
    & docker compose @composeArgs down --remove-orphans 2>$null
} catch {}

$networkName = 'access-security-net'
$containers = @(docker ps -aq --filter "network=$networkName")
if ($containers.Count -gt 0) {
    Write-Host "Removing containers attached to $networkName..." -ForegroundColor Yellow
    & docker rm -f $containers
}

try {
    & docker network rm $networkName 2>$null
} catch {}

Write-Host 'Starting compose stack...' -ForegroundColor Cyan
if ($SkipBuild) {
    & docker compose @composeArgs up -d
} else {
    & docker compose @composeArgs up -d --build
}

if ($LASTEXITCODE -ne 0) {
    Write-Host 'Failed to start full stack.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host 'Full stack started successfully.' -ForegroundColor Green

if ($Verify) {
    $verifyScript = Join-Path $PSScriptRoot 'Minimal-Service-Test.ps1'
    & powershell -ExecutionPolicy Bypass -File $verifyScript
    exit $LASTEXITCODE
}

exit 0
