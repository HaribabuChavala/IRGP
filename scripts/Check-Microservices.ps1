$checks = @(
    @{ Name = 'Traefik Dashboard'; Url = 'http://localhost:8088/dashboard/' },
    @{ Name = 'Keycloak Realm'; Url = 'http://localhost:8081/realms/report-platform' },
    @{ Name = 'API'; Url = 'http://report.localhost/health' },
    @{ Name = 'UI'; Url = 'http://app.localhost' },
    @{ Name = 'Auth'; Url = 'http://auth.localhost/health' },
    @{ Name = 'Users'; Url = 'http://users.localhost/health' },
    @{ Name = 'Organizations'; Url = 'http://orgs.localhost/health' },
    @{ Name = 'Platform Admin'; Url = 'http://platform-admin.localhost/health' },
    @{ Name = 'Portal'; Url = 'http://portal.localhost/health' },
    @{ Name = 'Subscriptions'; Url = 'http://subscriptions.localhost/health' },
    @{ Name = 'Notifications'; Url = 'http://notifications.localhost/health' },
    @{ Name = 'Reminders'; Url = 'http://reminders.localhost/health' },
    @{ Name = 'Data Sources'; Url = 'http://datasources.localhost/health' },
    @{ Name = 'Reports'; Url = 'http://reports.localhost/health' },
    @{ Name = 'Audit'; Url = 'http://audit.localhost/health' },
    @{ Name = 'Scheduler'; Url = 'http://scheduler.localhost/health' },
    @{ Name = 'Observability'; Url = 'http://observability.localhost/health' },
    @{ Name = 'Export'; Url = 'http://export.localhost/health' },
    @{ Name = 'Billing'; Url = 'http://billing.localhost/health' }
)

$failures = 0

foreach ($check in $checks) {
    try {
        $response = Invoke-WebRequest -Uri $check.Url -Method Get -TimeoutSec 10 -UseBasicParsing
        $status = [int]$response.StatusCode
        if ($status -ge 200 -and $status -lt 400) {
            Write-Host "PASS [$($check.Name)] $($check.Url) -> HTTP $status" -ForegroundColor Green
        } else {
            Write-Host "FAIL [$($check.Name)] $($check.Url) -> HTTP $status" -ForegroundColor Red
            $failures++
        }
    }
    catch {
        Write-Host "FAIL [$($check.Name)] $($check.Url) -> unavailable" -ForegroundColor Red
        $failures++
    }
}

if ($failures -gt 0) {
    Write-Host "`nHealth check failed for $failures service(s)." -ForegroundColor Red
    exit 1
}

Write-Host "`nAll configured services are responding." -ForegroundColor Green
