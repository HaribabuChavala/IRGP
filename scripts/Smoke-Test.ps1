$baseChecks = @(
    'http://localhost:8088/dashboard/',
    'http://localhost:8081/realms/report-platform',
    'http://report.localhost/health',
    'http://app.localhost',
    'http://auth.localhost/health',
    'http://users.localhost/health',
    'http://orgs.localhost/health',
    'http://platform-admin.localhost/health',
    'http://portal.localhost/health',
    'http://subscriptions.localhost/health',
    'http://notifications.localhost/health',
    'http://reminders.localhost/health',
    'http://datasources.localhost/health',
    'http://reports.localhost/health',
    'http://audit.localhost/health',
    'http://scheduler.localhost/health',
    'http://observability.localhost/health',
    'http://export.localhost/health',
    'http://billing.localhost/health'
)

$failures = 0

foreach ($url in $baseChecks) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 10 -UseBasicParsing
        $status = [int]$response.StatusCode
        if ($status -ge 200 -and $status -lt 400) {
            Write-Host "PASS $url -> HTTP $status" -ForegroundColor Green
        } else {
            Write-Host "FAIL $url -> HTTP $status" -ForegroundColor Red
            $failures++
        }
    }
    catch {
        Write-Host "FAIL $url -> unavailable" -ForegroundColor Red
        $failures++
    }
}

if ($failures -gt 0) {
    Write-Host "`nSmoke test failed for $failures endpoint(s)." -ForegroundColor Red
    exit 1
}

Write-Host "`nSmoke test passed — all endpoints responded successfully." -ForegroundColor Green
