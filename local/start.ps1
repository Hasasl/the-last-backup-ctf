$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$projectRoot = Split-Path $PSScriptRoot -Parent
$dockerPath = Get-DockerPath
Push-Location $projectRoot
try {
    & $dockerPath compose --env-file local/.env -f compose.local.yml up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'Docker startup failed. Open Docker Desktop and try again.' }
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8001/' -TimeoutSec 3
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw 'CTFd is still starting. Check its Docker logs, then try again.' }
    & $dockerPath compose --env-file local/.env -f compose.local.yml exec -T ctfd python /bootstrap/bootstrap_full.py
    if ($LASTEXITCODE -ne 0) { throw 'Event initialization failed. Existing event data has not been replaced.' }
    & $dockerPath compose --env-file local/.env -f compose.local.yml exec -T ctfd python /bootstrap/activate_theme.py
    if ($LASTEXITCODE -ne 0) { throw 'The Northstar theme could not be activated.' }
    Write-Host 'Full CTFd: http://localhost:8001'
    Write-Host 'Archive: http://localhost:8081 | Portal: http://localhost:8083 | Verifier: http://localhost:8443'
    Write-Host 'To reset the box later, double-click "Reset Box.cmd" (see README-LOCAL.md).'
} finally { Pop-Location }
