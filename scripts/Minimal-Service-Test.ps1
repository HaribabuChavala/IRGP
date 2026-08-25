$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host '=== Minimal service health test ===' -ForegroundColor Cyan
$checkScript = Join-Path $PSScriptRoot 'Check-Microservices.ps1'
$global:LASTEXITCODE = 0
& $checkScript
if ($global:LASTEXITCODE -ne 0) {
    Write-Host "Service health checks failed." -ForegroundColor Red
    exit $global:LASTEXITCODE
}

Write-Host "`n=== Oracle seeded data test (readonly user) ===" -ForegroundColor Cyan
$oracleCustomers = docker exec access-oracle bash -lc "echo 'select count(*) from report_owner.customers;' | sqlplus -s report_ro/ReportReadOnly123@localhost:1521/FREEPDB1"
$oracleOrders = docker exec access-oracle bash -lc "echo 'select count(*) from report_owner.sales_orders;' | sqlplus -s report_ro/ReportReadOnly123@localhost:1521/FREEPDB1"

$oracleCustomerCount = [int](($oracleCustomers | Select-String '^\s*\d+\s*$' | Select-Object -Last 1).ToString().Trim())
$oracleOrderCount = [int](($oracleOrders | Select-String '^\s*\d+\s*$' | Select-Object -Last 1).ToString().Trim())

if ($oracleCustomerCount -lt 1 -or $oracleOrderCount -lt 1) {
    Write-Host "Oracle data check failed. customers=$oracleCustomerCount sales_orders=$oracleOrderCount" -ForegroundColor Red
    exit 1
}
Write-Host "PASS Oracle rows: customers=$oracleCustomerCount sales_orders=$oracleOrderCount" -ForegroundColor Green

Write-Host "`n=== Teradata-lab seeded data test (readonly user) ===" -ForegroundColor Cyan
$teradataCustomers = docker exec access-teradata-lab psql -U td_readonly -d teradata_lab -t -A -c "select count(*) from public.customers;"
$teradataOrders = docker exec access-teradata-lab psql -U td_readonly -d teradata_lab -t -A -c "select count(*) from public.sales_orders;"

$teradataCustomerCount = [int]($teradataCustomers.Trim())
$teradataOrderCount = [int]($teradataOrders.Trim())

if ($teradataCustomerCount -lt 1 -or $teradataOrderCount -lt 1) {
    Write-Host "Teradata-lab data check failed. customers=$teradataCustomerCount sales_orders=$teradataOrderCount" -ForegroundColor Red
    exit 1
}
Write-Host "PASS Teradata-lab rows: customers=$teradataCustomerCount sales_orders=$teradataOrderCount" -ForegroundColor Green

Write-Host "`nMinimal test passed: all routed services responded and DB seeded data is accessible." -ForegroundColor Green
exit 0
