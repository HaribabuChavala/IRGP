param(
    [switch]$Verify,
    [int]$VerifyAttempts = 6,
    [int]$VerifyDelaySeconds = 10
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$composeArgs = @(
    '-f', 'docker-compose.yml',
    '-f', 'docker-compose.override.yml',
    '-f', 'docker-compose.microservices.yml'
)

Write-Host 'Starting full stack with merged compose files...' -ForegroundColor Cyan
& docker compose @composeArgs up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Failed to start full stack.' -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nFull stack started successfully." -ForegroundColor Green

if ($Verify) {
    $verifyScript = Join-Path $PSScriptRoot 'Minimal-Service-Test.ps1'
    for ($attempt = 1; $attempt -le $VerifyAttempts; $attempt++) {
        Write-Host "`nRunning minimal verification (attempt $attempt of $VerifyAttempts)..." -ForegroundColor Cyan
        & powershell -ExecutionPolicy Bypass -File $verifyScript

        if ($LASTEXITCODE -eq 0) {
            exit 0
        }

        if ($attempt -lt $VerifyAttempts) {
            Write-Host "Verification not ready yet. Waiting $VerifyDelaySeconds seconds before retry..." -ForegroundColor Yellow
            Start-Sleep -Seconds $VerifyDelaySeconds
        }
    }

    Write-Host "Verification failed after $VerifyAttempts attempt(s)." -ForegroundColor Red
    exit 1
}

exit 0
