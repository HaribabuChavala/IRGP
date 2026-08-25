$ErrorActionPreference = 'Stop'

$checkScript = Join-Path $PSScriptRoot 'Check-Microservices.ps1'
$smokeScript = Join-Path $PSScriptRoot 'Smoke-Test.ps1'

Write-Host "=== Microservice health check ===" -ForegroundColor Cyan
& $checkScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "`n=== End-to-end smoke test ===" -ForegroundColor Cyan
& $smokeScript
exit $LASTEXITCODE
