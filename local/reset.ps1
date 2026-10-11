<#
.SYNOPSIS
  Reset The Last Backup (local Docker deployment) to its initial state.

.DESCRIPTION
  One entry point for every reset. Each action prints what it changed and then
  verifies the result, so the run doubles as reset-test evidence.

  -Linux       Restart the Linux evidence container: evidence is rebuilt from the
               read-only tar and the analyst scratch folder is wiped. SSH host key kept.
  -Portal      Invalidate every player's review session (rotates PORTAL_SECRET in
               local/.env, recreates the portal container).
  -Verifier    Clear completions, attempts and sign-in throttle. Add -Team <id> for one
               team, otherwise all teams. Teams and tokens are kept.
  -Scores      CTFd: delete all solves, wrong attempts, awards and hint purchases.
               Accounts, challenges, flags and hints are kept.
  -Players     CTFd: -Scores plus delete every non-admin player account.
  -All         -Linux -Portal -Verifier(all teams) -Scores  (a clean slate for a new
               session; players keep their accounts).
  -FullWipe    Delete ALL Docker volumes and rebuild from scratch (CTFd database,
               uploads, verifier state, SSH host key). Reissues the demo verifier token
               and refreshes local/private/known_hosts.
  -Backup      Save a backup now (CTFd SQL + uploads + verifier SQLite) in backups\<time>.
  -Status      Show container state and the health of all five player-facing services.
  -DryRun      With -Scores/-Players/-Verifier: only report what would be deleted.
  -Yes         Do not ask for confirmation.   -NoBackup  Skip the automatic backup that
               normally runs before -Scores, -Players, -All and -FullWipe.

.EXAMPLE
  .\local\reset.ps1 -Linux
  .\local\reset.ps1 -Verifier -Team team-01
  .\local\reset.ps1 -Scores -DryRun
  .\local\reset.ps1 -All
  .\local\reset.ps1 -FullWipe
#>
[CmdletBinding()]
param(
    [switch]$Linux, [switch]$Portal, [switch]$Verifier, [string]$Team = '',
    [switch]$Scores, [switch]$Players, [switch]$All, [switch]$FullWipe,
    [switch]$Backup, [switch]$Status, [switch]$DryRun, [switch]$Yes, [switch]$NoBackup
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$docker = Get-DockerPath
$results = New-Object System.Collections.ArrayList

# ---------- helpers ----------
function Compose {
    $ErrorActionPreference = 'Continue'
    & $docker compose --env-file local/.env -f compose.local.yml @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') failed (exit $LASTEXITCODE)" }
}
function ComposeStdin([string]$text, [string[]]$composeArgs) {
    $ErrorActionPreference = 'Continue'
    $text | & $docker compose --env-file local/.env -f compose.local.yml @composeArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($composeArgs -join ' ') failed (exit $LASTEXITCODE)" }
}
function Get-ResetJson($output) {
    $line = ($output | Out-String) -split "`n" | Where-Object { $_ -like '*RESET_JSON:*' } | Select-Object -Last 1
    if (-not $line) { throw "No RESET_JSON result returned:`n$($output | Out-String)" }
    return ($line.Substring($line.IndexOf('RESET_JSON:') + 11).Trim() | ConvertFrom-Json)
}
function Step([string]$name, [scriptblock]$body) {
    Write-Host ""
    Write-Host "== $name" -ForegroundColor Cyan
    try {
        & $body
        [void]$results.Add([pscustomobject]@{ Step = $name; Result = 'OK' })
    } catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
        [void]$results.Add([pscustomobject]@{ Step = $name; Result = 'FAILED' })
    }
}
function Wait-Http([string]$url, [int]$seconds = 60) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    }
    throw "$url did not become healthy within $seconds s"
}
function Confirm-Action([string]$what, [string]$word = 'yes') {
    if ($Yes -or $DryRun) { return }
    $answer = Read-Host "$what`nType '$word' to continue"
    if ($answer -ne $word) { throw 'Cancelled by user.' }
}
function Invoke-Backup {
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $dir = Join-Path $root "backups\$stamp"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Compose exec -T database sh -c 'exec mariadb-dump -uroot -p$MARIADB_ROOT_PASSWORD --single-transaction ctfd > /tmp/ctfd.sql'
    Compose cp database:/tmp/ctfd.sql (Join-Path $dir 'ctfd.sql')
    Compose exec -T database rm -f /tmp/ctfd.sql
    New-Item -ItemType Directory -Force -Path (Join-Path $dir 'uploads') | Out-Null
    Compose cp ctfd:/var/uploads/. (Join-Path $dir 'uploads')
    $py = "import sqlite3`ns=sqlite3.connect('/state/verifier.sqlite')`nd=sqlite3.connect('/state/backup-tmp.sqlite')`ns.backup(d)`nd.close()`ns.close()`nprint('verifier snapshot ok')`n"
    ComposeStdin $py @('exec', '-T', 'verifier', 'python', '-')
    Compose cp verifier:/state/backup-tmp.sqlite (Join-Path $dir 'verifier.sqlite')
    Compose exec -T verifier rm -f /state/backup-tmp.sqlite
    if ((Get-Item (Join-Path $dir 'ctfd.sql')).Length -lt 1000) { throw 'ctfd.sql looks empty' }
    Write-Host "Backup saved in $dir (private: contains password hashes and flags)"
}
function Reset-Linux {
    if ($DryRun) { Write-Host 'Dry run: would restart the linux container (wipes scratch, rebuilds evidence).'; return }
    Compose restart linux
    $up = $false
    for ($i = 0; $i -lt 30 -and -not $up; $i++) {
        try { $o = Compose exec -T linux sh -c 'test -s /run/analyst_authorized_keys && echo UP'; if (($o | Out-String) -match 'UP') { $up = $true } } catch { }
        if (-not $up) { Start-Sleep -Seconds 2 }
    }
    if (-not $up) { throw 'Linux container did not come back (check: docker compose logs linux)' }
    $o = Compose exec -T linux sh -c 'test $(ls -A /home/analyst/work | wc -l) -eq 0 && test -s /srv/northstar/routes/EXIT-04.route && echo SCRATCH_EMPTY_EVIDENCE_PRESENT'
    if (($o | Out-String) -notmatch 'SCRATCH_EMPTY_EVIDENCE_PRESENT') { throw 'Verification failed: scratch not empty or evidence missing' }
    Write-Host 'Verified: analyst scratch folder is empty and evidence is rebuilt.'
}
function Reset-Portal {
    if ($DryRun) { Write-Host 'Dry run: would rotate PORTAL_SECRET and recreate the portal.'; return }
    $envPath = Join-Path $root 'local\.env'
    $text = [IO.File]::ReadAllText($envPath)
    if ($text -notmatch '(?m)^PORTAL_SECRET=') { throw 'PORTAL_SECRET not found in local/.env' }
    $bytes = New-Object byte[] 24
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $new = -join ($bytes | ForEach-Object { $_.ToString('x2') })
    $text = [regex]::Replace($text, '(?m)^PORTAL_SECRET=[^\r\n]*', "PORTAL_SECRET=$new")
    [IO.File]::WriteAllText($envPath, $text, (New-Object Text.UTF8Encoding $false))
    Compose up -d --force-recreate portal
    Wait-Http 'http://127.0.0.1:8083/health' 60
    Write-Host 'Verified: portal recreated with a new secret and healthy. All earlier review sessions are now invalid.'
}
function Reset-Verifier {
    $script = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'reset_verifier.py'))
    $dry = if ($DryRun) { '1' } else { '0' }
    $o = ComposeStdin $script @('exec', '-T', '-e', "RESET_TEAM=$Team", '-e', "RESET_DRY=$dry", 'verifier', 'python', '-')
    $r = Get-ResetJson $o
    Write-Host ("Team: {0} | cleared completions={1} attempts={2} logins={3}" -f $r.team, $r.cleared.completions, $r.cleared.attempts, $r.cleared.logins)
    if (-not $DryRun) {
        if ($r.remaining.completions -ne 0 -or $r.remaining.attempts -ne 0) { throw 'Verification failed: rows remain' }
        Write-Host ("Verified: 0 completions and 0 attempts remain; {0} team token(s) kept." -f $r.teams_kept)
    } else { Write-Host 'Dry run: nothing was changed.' }
    Wait-Http 'http://127.0.0.1:8443/health' 30
}
function Reset-Ctfd([string]$mode) {
    $script = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'reset_ctfd.py'))
    $dry = if ($DryRun) { '1' } else { '0' }
    $o = ComposeStdin $script @('exec', '-T', '-e', "RESET_MODE=$mode", '-e', "RESET_DRY=$dry", 'ctfd', 'python', '-')
    $r = Get-ResetJson $o
    Write-Host ("Mode: {0} | cleared: solves={1} fails={2} submissions={3} awards={4} hint purchases={5} players={6}" -f `
        $r.mode, $r.cleared.solves, $r.cleared.fails, $r.cleared.submissions, $r.cleared.awards, $r.cleared.unlocks, $r.cleared.users)
    if ($DryRun) { Write-Host 'Dry run: nothing was changed.'; return }
    if ($r.remaining.solves -ne 0 -or $r.remaining.submissions -ne 0 -or $r.remaining.unlocks -ne 0 -or $r.remaining.awards -ne 0) { throw 'Verification failed: progress rows remain' }
    if ($r.kept.challenges -lt 1) { throw 'Safety check failed: no challenges found after reset' }
    Write-Host ("Verified: no solves/attempts/hint purchases remain. Kept: {0} challenges, {1} flags, {2} hints, {3} admin(s)." -f $r.kept.challenges, $r.kept.flags, $r.kept.hints, $r.kept.admins)
}
function Reset-Full {
    Compose down -v --remove-orphans
    $kh = Join-Path $root 'local\private\known_hosts'
    if (Test-Path $kh) { Remove-Item $kh -Force }
    & (Join-Path $PSScriptRoot 'start.ps1')
    Wait-Http 'http://127.0.0.1:8443/health' 90
    # Fresh SSH host key -> refresh the pinned known_hosts used by the documented ssh command.
    $keyscan = Get-Command ssh-keyscan -ErrorAction SilentlyContinue
    if ($keyscan) {
        $lines = $null
        for ($i = 0; $i -lt 10 -and -not $lines; $i++) {
            $ErrorActionPreference = 'Continue'
            $lines = & $keyscan.Source -t ed25519 -p 2222 127.0.0.1 2>$null | Where-Object { $_ -and $_ -notlike '#*' }
            $ErrorActionPreference = 'Stop'
            if (-not $lines) { Start-Sleep -Seconds 2 }
        }
        if ($lines) { [IO.File]::WriteAllText($kh, (($lines -join "`n") + "`n")); Write-Host 'Refreshed local/private/known_hosts for the new SSH host key.' }
        else { Write-Warning 'Could not read the new SSH host key. Run ssh-keyscan manually.' }
    } else { Write-Warning 'ssh-keyscan not found; recreate local/private/known_hosts before using SSH.' }
    # The verifier database was wiped, so the demo team token must be issued again.
    $o = Compose exec -T verifier python manage.py issue-team demo --database /state/verifier.sqlite
    $token = (($o | Out-String).Trim() -split "`n" | Select-Object -Last 1).Trim()
    if ($token.Length -lt 20) { throw 'Demo token was not issued' }
    [IO.File]::WriteAllText((Join-Path $root 'local\private\demo-verifier-token.txt'), $token)
    $la = Join-Path $root 'LOCAL-ACCESS.txt'
    if (Test-Path $la) {
        $t = [IO.File]::ReadAllText($la)
        [IO.File]::WriteAllText($la, [regex]::Replace($t, '(?m)^Demo token: [^\r\n]*', "Demo token: $token"))
    }
    Write-Host 'Issued a new demo verifier token (saved to LOCAL-ACCESS.txt).'
    Write-Host 'Note: all players, scores and verifier progress are gone; register players again.'
}

# ---------- argument handling ----------
$anyAction = $Linux -or $Portal -or $Verifier -or $Scores -or $Players -or $All -or $FullWipe -or $Backup -or $Status
if (-not $anyAction) { Get-Help $MyInvocation.MyCommand.Path -Detailed; exit 0 }
if ($All) { $Linux = $true; $Portal = $true; $Verifier = $true; $Scores = $true }
if ($Players) { $Scores = $false }
if ($FullWipe -and ($Linux -or $Portal -or $Verifier -or $Scores -or $Players)) {
    Write-Host '-FullWipe already resets everything; the other switches are ignored.'
    $Linux = $false; $Portal = $false; $Verifier = $false; $Scores = $false; $Players = $false
}

if ($Status) {
    Step 'Status' {
        Compose ps
        foreach ($u in 'http://127.0.0.1:8001/', 'http://127.0.0.1:8081/', 'http://127.0.0.1:8083/health', 'http://127.0.0.1:8443/health') {
            try { $r = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 5; Write-Host ("{0,-34} HTTP {1}" -f $u, $r.StatusCode) }
            catch { Write-Host ("{0,-34} DOWN" -f $u) -ForegroundColor Red }
        }
        $ErrorActionPreference = 'Continue'
        $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port 2222 -WarningAction SilentlyContinue
        Write-Host ("{0,-34} {1}" -f '127.0.0.1:2222 (SSH)', $(if ($tcp.TcpTestSucceeded) { 'open' } else { 'DOWN' }))
    }
}

$destructive = ($Scores -or $Players -or $FullWipe) -and -not $DryRun
if ($destructive -and -not $NoBackup -and -not $Backup) {
    if ($FullWipe -or $Players -or $Scores) { $Backup = $true }
}

if ($Backup) { Step 'Backup' { Invoke-Backup } }
if ($results | Where-Object { $_.Step -eq 'Backup' -and $_.Result -eq 'FAILED' }) {
    if ($destructive) { Write-Host 'Backup failed - refusing to run destructive resets. Use -NoBackup to override.' -ForegroundColor Red; $results | Format-Table -AutoSize; exit 1 }
}

if ($FullWipe) {
    Step 'Full wipe (all volumes) and rebuild' {
        Confirm-Action 'This DELETES all players, scores, uploads and verifier progress and rebuilds the box.' 'RESET'
        Reset-Full
    }
} else {
    if ($Linux)    { Step 'Reset Linux evidence container' { Reset-Linux } }
    if ($Portal)   { Step 'Reset evidence portal sessions' { Reset-Portal } }
    if ($Verifier) { Step ('Reset verifier progress' + $(if ($Team) { " (team $Team)" } else { ' (all teams)' })) { Reset-Verifier } }
    if ($Scores)   { Step 'Reset CTFd scores (accounts kept)' { Confirm-Action 'This deletes ALL solves, attempts and hint purchases.'; Reset-Ctfd 'scores' } }
    if ($Players)  { Step 'Reset CTFd scores AND delete player accounts' { Confirm-Action 'This deletes ALL player accounts and their progress.'; Reset-Ctfd 'players' } }
}

Write-Host ""
Write-Host "================ Summary ================" -ForegroundColor Cyan
$results | Format-Table -AutoSize
if ($results | Where-Object { $_.Result -eq 'FAILED' }) { exit 1 }
