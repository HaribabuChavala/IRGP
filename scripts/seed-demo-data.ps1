$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host 'Seeding demo data into PostgreSQL...' -ForegroundColor Cyan
Get-Content .\postgres\seed\demo-data.sql | docker exec -i access-postgres psql -U admin -d report_platform

if ($LASTEXITCODE -ne 0) {
    throw 'Demo data seed failed.'
}

Write-Host 'Demo data seeded successfully.' -ForegroundColor Green
