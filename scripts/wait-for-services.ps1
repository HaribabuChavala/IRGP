$ServiceUrls = @(
  'http://localhost:8088/dashboard/',
  'http://localhost:8081/realms/report-platform',
  'http://report.localhost/health',
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

Write-Host "Waiting for services to come online..." -ForegroundColor Cyan
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    $allReady = $true

    foreach ($url in $ServiceUrls) {
        try {
            $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
                $allReady = $false
            }
        }
        catch {
            $allReady = $false
        }
    }

    if ($allReady) {
        $ready = $true
        break
    }

    Write-Host "Attempt ${attempt}/${maxAttempts}: waiting for services..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    Write-Host "Timed out waiting for services to become ready." -ForegroundColor Red
    exit 1
}

Write-Host "All configured services are ready." -ForegroundColor Green
