# Phase 4.8F lifecycle verification of scripts\ops\footiq_service.ps1 on a PRIVATE COPY of production, port 8123, private lock/run/log folders.
# The scheduler is left ON (config live_enabled true) to prove the one-scheduler rule, but the private copy's next check is hours away, so no provider request can occur (the production
# request ledger is compared before and after). Production's database file is only read once (SQLite backup API) and its hash is compared at the end.
$ErrorActionPreference = 'Stop'
$Root = 'D:\Foot IQ'
$Svc = Join-Path $Root 'scripts\ops\footiq_service.ps1'
$T = Join-Path $Root 'data\supervised\phase4\p48f\lifecycle_work'
if (Test-Path $T) { Remove-Item $T -Recurse -Force }
New-Item -ItemType Directory -Force -Path $T | Out-Null
$Evidence = Join-Path $Root 'data\supervised\phase4\p48f\lifecycle_evidence.txt'
Set-Content $Evidence "FootIQ service lifecycle check $(Get-Date -Format u)`n"
function Say($m) { Write-Host $m; Add-Content $Evidence $m }
$prodHash = (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash
$ledger = Join-Path $Root 'data\snapshots\request_ledger.jsonl'
$ledgerBefore = (Get-Content $ledger).Count

# private copy (consistent SQLite backup, production opened read-only)
& (Join-Path $Root '.venv\Scripts\python.exe') -B -c "import sqlite3;s=sqlite3.connect('file:D:/Foot IQ/data/footiq.sqlite?mode=ro',uri=True);d=sqlite3.connect(r'$T\copy.sqlite');s.backup(d);d.close()"
$env:FOOTIQ_PORT = '8123'
$env:FOOTIQ_STORE_PATH = "$T\copy.sqlite"
$env:FOOTIQ_SCHEDULER_LOCK = "$T\scheduler.lock"
$env:FOOTIQ_RUN_DIR = "$T\run"
$env:FOOTIQ_LOG_DIR = "$T\logs"
Remove-Item Env:FOOTIQ_DISABLE_SYNC -ErrorAction SilentlyContinue

function Json($port, $path) { try { Invoke-RestMethod -Uri "http://127.0.0.1:$port$path" -TimeoutSec 10 } catch { $null } }
function PowerShellRun($arg) { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Svc @arg 2>&1 | Out-String }

Say "== 1. status before start"
Say (PowerShellRun @('status'))
Say "== 2. start"
Say (PowerShellRun @('start'))
$s = Json 8123 '/api/sync/status'
Say ("scheduler: {0} | threads={1} | lock={2} | next={3} | competitions={4} | pid={5}" -f $s.scheduler.status, $s.scheduler.active_scheduler_threads, $s.scheduler.lock_state, $s.scheduler.next_scheduled_check_utc, ($s.scheduler.enabled_competitions -join ','), $s.scheduler.process_id)
$pid1 = $s.scheduler.process_id

Say "== 3. start again (must say already running, no second backend)"
Say (PowerShellRun @('start'))
Say ("python/uvicorn processes listening on 8123: {0}" -f (Get-NetTCPConnection -LocalPort 8123 -State Listen | Measure-Object).Count)

Say "== 4. a second supervisor in the foreground must refuse (exit code 3)"
$o = PowerShellRun @('run'); Say $o; Say ("exit code: {0}" -f $LASTEXITCODE)

Say "== 5. a second backend on port 8124 with the SAME lock must not start a scheduler"
$p2 = Start-Process -FilePath (Join-Path $Root '.venv\Scripts\python.exe') -ArgumentList @('-X', 'utf8', '-m', 'uvicorn', 'main:app', '--app-dir', 'app', '--host', '127.0.0.1', '--port', '8124') -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput "$T\b2.out" -RedirectStandardError "$T\b2.err"
for ($i = 0; $i -lt 40; $i++) { Start-Sleep -Seconds 2; if (Json 8124 '/api/health') { break } }
Start-Sleep -Seconds 8
$s2 = Json 8124 '/api/sync/status'
Say ("second backend: threads={0} | lock={1} | status={2}" -f $s2.scheduler.active_scheduler_threads, $s2.scheduler.lock_state, $s2.scheduler.status)
Say ("first backend still: threads={0} | lock={1}" -f (Json 8123 '/api/sync/status').scheduler.active_scheduler_threads, (Json 8123 '/api/sync/status').scheduler.lock_state)
& taskkill.exe /T /F /PID $p2.Id | Out-Null

Say "== 6. crash: kill the backend tree; the supervisor must restart it, with no early provider request"
$child = [int](Get-Content "$T\run\backend-8123.pid")
$dueBefore = (Json 8123 '/api/sync/status').scheduler.next_scheduled_check_utc
& taskkill.exe /T /F /PID $child | Out-Null
$up = $false
for ($i = 0; $i -lt 45; $i++) { Start-Sleep -Seconds 2; $h = Json 8123 '/api/health'; if ($h -and ([int](Get-Content "$T\run\backend-8123.pid")) -ne $child) { $up = $true; break } }
Start-Sleep -Seconds 8
$s3 = Json 8123 '/api/sync/status'
Say ("restarted: {0} | new pid file {1} (old {2}) | scheduler pid {3} (before {4}) | threads={5} | next={6} (before {7})" -f $up, (Get-Content "$T\run\backend-8123.pid"), $child, $s3.scheduler.process_id, $pid1, $s3.scheduler.active_scheduler_threads, $s3.scheduler.next_scheduled_check_utc, $dueBefore)
Say "supervisor.log:"
Say ((Get-Content "$T\logs\supervisor.log" | Select-Object -Last 8) -join "`n")

Say "== 7. status, then stop"
Say (PowerShellRun @('status'))
Say (PowerShellRun @('stop'))
Say ("listeners on 8123 after stop: {0}; pid files left: {1}" -f (Get-NetTCPConnection -LocalPort 8123 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count, (Get-ChildItem "$T\run" -ErrorAction SilentlyContinue | Measure-Object).Count)
& (Join-Path $Root '.venv\Scripts\python.exe') -B -c "import sys;sys.path.insert(0,r'D:/Foot IQ/app');from store import sync;l=sync.SchedulerLock(r'$T\scheduler.lock');print('scheduler lock free after stop:', l.acquire());l.release()" | ForEach-Object { Say $_ }

Say "== 8. FOOTIQ_DISABLE_SYNC=1 still disables the scheduler"
$env:FOOTIQ_DISABLE_SYNC = '1'
Say (PowerShellRun @('start'))
$s4 = Json 8123 '/api/sync/status'
Say ("scheduler: {0} | threads={1} | lock={2}" -f $s4.scheduler.status, $s4.scheduler.active_scheduler_threads, $s4.scheduler.lock_state)
Say (PowerShellRun @('stop'))
Remove-Item Env:FOOTIQ_DISABLE_SYNC

Say "== 9. start refuses when the port is already taken by something else"
$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 8123); $listener.Start()
$o = PowerShellRun @('start'); Say $o; Say ("exit code: {0}" -f $LASTEXITCODE)
$listener.Stop()

Say "== 10. production untouched"
$prodAfter = (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash
Say ("production hash unchanged: {0}" -f ($prodHash -eq $prodAfter))
Say ("production request ledger lines before/after: {0}/{1}" -f $ledgerBefore, (Get-Content $ledger).Count)
Remove-Item "$T\copy.sqlite*" -Force -ErrorAction SilentlyContinue
