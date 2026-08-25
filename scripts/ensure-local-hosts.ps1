$ErrorActionPreference = 'Stop'

$hostsPath = [System.IO.Path]::Combine($env:SystemRoot, 'System32\drivers\etc\hosts')
$entries = @(
    '127.0.0.1 report.localhost',
    '127.0.0.1 app.localhost',
    '127.0.0.1 auth.localhost',
    '127.0.0.1 users.localhost',
    '127.0.0.1 orgs.localhost',
    '127.0.0.1 platform-admin.localhost',
    '127.0.0.1 portal.localhost',
    '127.0.0.1 subscriptions.localhost',
    '127.0.0.1 notifications.localhost',
    '127.0.0.1 reminders.localhost',
    '127.0.0.1 datasources.localhost',
    '127.0.0.1 reports.localhost',
    '127.0.0.1 audit.localhost',
    '127.0.0.1 scheduler.localhost',
    '127.0.0.1 observability.localhost',
    '127.0.0.1 export.localhost',
    '127.0.0.1 billing.localhost'
)

if (-not (Test-Path $hostsPath)) {
    throw "Hosts file not found at $hostsPath"
}

$existing = Get-Content -Path $hostsPath -ErrorAction SilentlyContinue
$missing = @()

foreach ($entry in $entries) {
    if (-not ($existing -match [regex]::Escape($entry))) {
        $missing += $entry
    }
}

if ($missing.Count -eq 0) {
    Write-Host 'Localhost aliases already present in hosts file.' -ForegroundColor Green
    exit 0
}

$formatted = @(
    '',
    '# Added by access-security-lab startup scripts',
    $missing
)

try {
    Add-Content -Path $hostsPath -Value $formatted -Encoding ASCII
    Write-Host 'Added missing localhost aliases to hosts file:' -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 0
}
catch {
    Write-Error "Unable to update hosts file. Run PowerShell as Administrator and try again."
    exit 1
}
