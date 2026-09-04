# Determine repository root (one level above scripts directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir '..') | Select-Object -ExpandProperty Path
Set-Location $root
$srcRoot = Join-Path $root 'microservices'
$dstRoot = Join-Path $root 'IRGP'
if (-Not (Test-Path $srcRoot)) { Write-Host "No microservices folder found at $srcRoot"; exit 1 }
Get-ChildItem -Path $srcRoot -Directory | ForEach-Object {
    $src = $_.FullName
    $dst = Join-Path $dstRoot $_.Name
    Write-Host "Syncing $src -> $dst"
    robocopy $src $dst /MIR /Z /FFT /NDL /NFL /NJH /NJS | Out-Null
}
Write-Host "Removing original microservices folder: $srcRoot"
Remove-Item -LiteralPath $srcRoot -Recurse -Force
Write-Host "MOVE_DONE"

